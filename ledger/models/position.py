import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid5

from django.db import models

from accounts.models import Account
from ledger.margin.closer import MARGIN_INSURANCE_ACCOUNT, MARGIN_POOL_ACCOUNT
from ledger.utils.external_price import SHORT, LONG, BUY, SELL, get_other_side
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import floor_precision, ceil_precision
from ledger.utils.price import get_last_price, get_depth_price
from market.models import PairSymbol

logger = logging.getLogger(__name__)


class MarginPosition(models.Model):
    DEFAULT_LIQUIDATION_LEVEL = Decimal('1.1')
    DEFAULT_INSURANCE_FEE_PERCENTAGE = Decimal('0.02')
    DEFAULT_INTEREST_FEE_PERCENTAGE = Decimal('0.00005')

    OPEN, CLOSED, TERMINATING = 'open', 'closed', 'terminating'
    STATUS_CHOICES = [(OPEN, OPEN), (CLOSED, CLOSED), (TERMINATING, TERMINATING)]
    SIDE_CHOICES = [(LONG, LONG), (SHORT, SHORT)]

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    wallet = models.OneToOneField('ledger.Wallet', on_delete=models.PROTECT)

    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.PROTECT)
    amount = get_amount_field(default=0)
    average_price = get_amount_field(default=0)
    liquidation_price = get_amount_field(null=True)
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    status = models.CharField(default=OPEN, max_length=12, choices=STATUS_CHOICES)
    leverage = models.IntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['side', 'status', 'symbol', 'liquidation_price'], name="position_idx")
        ]

    @property
    def variant(self):
        return self.wallet.variant

    @property
    def margin_base_wallet(self):
        return self.symbol.base_asset.get_wallet(self.account, self.wallet.MARGIN, self.wallet.variant)

    @property
    def margin_wallet(self):
        return self.symbol.asset.get_wallet(self.account, self.wallet.MARGIN, self.wallet.variant)

    @property
    def total_balance(self):
        return self.margin_base_wallet.get_free()

    @property
    def loan_wallet(self):
        loan_asset = self.symbol.asset if self.side == SHORT else self.symbol.base_asset
        return loan_asset.get_wallet(self.account, self.wallet.LOAN, self.wallet.variant)

    @property
    def debt_amount(self):
        return -self.loan_wallet.balance

    @property
    def withdrawable_base_asset(self):
        return self.total_balance - self.total_debt * 2

    @property
    def total_debt(self):
        if self.side == SHORT:
            from market.models import Order
            price = get_last_price(self.symbol.name)
        else:
            price = Decimal('1')
        return self.debt_amount * price

    # todo :: handle different liquidation ratio for different leverage
    def update_liquidation_price(self, pipeline=None):
        if self.side == SHORT and self.leverage == 1:
            debt_amount = self.debt_amount
            total_balance = self.total_balance
            if pipeline:
                debt_amount -= pipeline.get_wallet_balance_diff(self.loan_wallet.id)
                total_balance += pipeline.get_wallet_balance_diff(self.margin_base_wallet.id)
            if debt_amount:
                self.liquidation_price = total_balance / (self.DEFAULT_LIQUIDATION_LEVEL * debt_amount)
            else:
                self.liquidation_price = None
        else:
            raise NotImplementedError

    @classmethod
    def get_by(cls, symbol: PairSymbol, account: Account, side=SHORT):
        from ledger.models import Wallet

        position = cls.objects.filter(
            account=account,
            symbol=symbol,
            status__in=[cls.OPEN, cls.TERMINATING],
            side=side,
        ).first()
        if not position:
            position, _ = cls.objects.get_or_create(
                account=account,
                symbol=symbol,
                status=cls.OPEN,
                defaults={
                    'wallet': symbol.asset.get_wallet(
                        account, Wallet.MARGIN, uuid5(uuid.NAMESPACE_X500, f'{account.id}-{symbol.name}-{side}')
                    ),
                    'side': side
                }
            )
        return position

    def has_enough_margin(self, extending_base_amount):
        if self.side == SHORT and self.leverage == 1:
            return self.withdrawable_base_asset >= extending_base_amount
        raise NotImplementedError

    def get_insurance_wallet(self):
        return self.symbol.base_asset.get_wallet(account=Account.objects.get(id=MARGIN_INSURANCE_ACCOUNT))

    def get_margin_pool_wallet(self):
        return self.symbol.base_asset.get_wallet(account=Account.objects.get(id=MARGIN_POOL_ACCOUNT))

    def liquidate(self, pipeline):
        if self.status != self.OPEN:
            return

        self.status = self.TERMINATING
        self.save(update_fields=['status'])

        from market.utils.order_utils import Order, new_order
        from ledger.models import Trx, Wallet

        Order.cancel_orders(Order.open_objects.filter(wallet=self.wallet))

        to_close_amount = ceil_precision((self.debt_amount - pipeline.get_wallet_balance_diff(self.loan_wallet.id))
                                         / (1 - self.symbol.taker_fee), self.symbol.step_size)

        side = BUY if self.side == SHORT else SELL
        price = get_depth_price(symbol=self.symbol.name, side=get_other_side(side), amount=to_close_amount)
        free_amount = floor_precision(self.margin_base_wallet.get_free() / price / (1 - self.symbol.taker_fee), self.symbol.step_size)

        loss_amount = (to_close_amount - free_amount) * price * Decimal('1.02')

        group_id = uuid.uuid4()
        if loss_amount > Decimal('0'):
            pipeline.new_trx(
                self.get_insurance_wallet(),
                self.margin_base_wallet,
                loss_amount,
                Trx.MARGIN_INSURANCE,
                group_id,
            )

        liquidation_order = new_order(
            pipeline=pipeline,
            symbol=self.symbol,
            account=self.account,
            amount=to_close_amount,
            fill_type=Order.MARKET,
            side=side,
            market=Wallet.MARGIN,
            variant=self.variant,
            pass_min_notional=True,
            order_type=Order.LIQUIDATION,
            parent_lock_group_id=group_id
        )

        margin_cross_wallet = self.margin_base_wallet.asset.get_wallet(self.account, market=Wallet.MARGIN, variant=None)
        remaining_balance = self.margin_base_wallet.balance + pipeline.get_wallet_balance_diff(
            self.margin_base_wallet.id)

        if remaining_balance > Decimal('0') and loss_amount > Decimal('0'):
            pipeline.new_trx(
                self.margin_base_wallet,
                self.get_insurance_wallet(),
                min(loss_amount, remaining_balance),
                Trx.MARGIN_INSURANCE,
                group_id,
            )
            remaining_balance -= min(loss_amount, remaining_balance)

        if remaining_balance > Decimal('0'):
            insurance_fee_amount = min(remaining_balance,
                                       to_close_amount * price * self.DEFAULT_INSURANCE_FEE_PERCENTAGE)
            if insurance_fee_amount > Decimal(0):
                pipeline.new_trx(
                    self.margin_base_wallet,
                    self.get_insurance_wallet(),
                    insurance_fee_amount,
                    Trx.LIQUID,
                    liquidation_order.group_id
                )
                remaining_balance -= insurance_fee_amount
            if remaining_balance > Decimal(0):
                pipeline.new_trx(
                    self.margin_base_wallet,
                    margin_cross_wallet,
                    remaining_balance,
                    Trx.LIQUID,
                    liquidation_order.group_id
                )

        liquidation_order.refresh_from_db()

        if liquidation_order.filled_amount >= self.debt_amount:
            self.amount = Decimal(0)
            self.status = self.CLOSED
        else:
            self.amount = max(self.debt_amount - liquidation_order.filled_amount, Decimal('0'))
            logger.warning(f'Position:{self.id} doesnt close in Liquidation Process Due to Order'
                           f' filled amount{liquidation_order.filled_amount}/{self.debt_amount}')

        if liquidation_order.filled_amount == Decimal('0') and liquidation_order.status == Order.CANCELED:
            self.status = self.OPEN

        self.save(update_fields=['amount', 'status'])
        self.update_liquidation_price(pipeline)

    @classmethod
    def check_for_liquidation(cls, order, min_price, max_price, pipeline):
        to_liquid_short_positions = cls.objects.filter(
            side=SHORT,
            status=cls.OPEN,
            symbol=order.symbol,
            liquidation_price__lte=max_price,
        ).order_by('liquidation_price')

        for position in to_liquid_short_positions:
            position.liquidate(pipeline)

        to_liquid_long_positions = cls.objects.filter(
            side=LONG,
            status=cls.OPEN,
            symbol=order.symbol,
            liquidation_price__gte=min_price,
        ).order_by('liquidation_price')

        for position in to_liquid_long_positions:
            position.liquidate(pipeline)


@dataclass
class MarginPositionTradeInfo:
    loan_type: str
    position: MarginPosition
    trade_amount: Decimal = 0
    trade_price: Decimal = 0
    group_id: UUID = 0
