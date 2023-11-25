import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Account
from ledger.margin.closer import MARGIN_INSURANCE_ACCOUNT, MARGIN_POOL_ACCOUNT
from ledger.models import Trx
from ledger.utils.external_price import SHORT, LONG, BUY, SELL, get_other_side
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import floor_precision, ceil_precision
from ledger.utils.price import get_depth_price, get_base_depth_price
from market.models import PairSymbol

logger = logging.getLogger(__name__)


class MarginPosition(models.Model):
    DEFAULT_LIQUIDATION_LEVEL = Decimal('1.1')
    DEFAULT_INSURANCE_FEE_PERCENTAGE = Decimal('0.02')
    DEFAULT_USDT_INTEREST_FEE_PERCENTAGE = Decimal('0.00009')
    DEFAULT_IRT_INTEREST_FEE_PERCENTAGE = Decimal('0.00025')

    OPEN, CLOSED, TERMINATING = 'open', 'closed', 'terminating'
    STATUS_CHOICES = [(OPEN, OPEN), (CLOSED, CLOSED), (TERMINATING, TERMINATING)]
    SIDE_CHOICES = [(LONG, LONG), (SHORT, SHORT)]

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    asset_wallet = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='asset_wallet')
    base_wallet = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='base_wallet')
    group_id = models.UUIDField(default=uuid.uuid4)

    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.PROTECT)
    amount = get_amount_field(default=0)
    average_price = get_amount_field(default=0)
    liquidation_price = get_amount_field(null=True)
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    status = models.CharField(default=OPEN, max_length=12, choices=STATUS_CHOICES)
    leverage = models.IntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'symbol', 'liquidation_price'], name="position_idx")
        ]

    @property
    def base_margin_wallet(self):
        return self.symbol.base_asset.get_wallet(self.account, self.asset_wallet.MARGIN, self.group_id)

    @property
    def asset_margin_wallet(self):
        return self.symbol.asset.get_wallet(self.account, self.asset_wallet.MARGIN, self.group_id)

    @property
    def variant(self):
        return self.group_id
    @property
    def loan_wallet(self):
        if self.side == SHORT:
            return self.asset_margin_wallet
        elif self.side == LONG:
            return self.base_margin_wallet
        else:
            raise NotImplementedError

    @property
    def total_balance(self):
        if self.side == SHORT:
            return self.base_margin_wallet.balance
        elif self.side == LONG:
            return self.asset_margin_wallet.balance
        else:
            raise NotImplementedError

    @property
    def equity(self):
        return self.base_margin_wallet.balance + self.asset_margin_wallet.balance * self.symbol.last_trade_price

    @property
    def base_debt_amount(self):
        if self.side == SHORT:
            return self.asset_margin_wallet.balance * self.symbol.last_trade_price
        elif self.side == LONG:
            return self.base_margin_wallet.balance
        else:
            raise NotImplementedError

    @property
    def debt_amount(self):
        return -self.loan_wallet.balance

    @property
    def withdrawable_base_asset(self):
        return max(self.base_margin_wallet.balance, Decimal('0')) + min(self.asset_margin_wallet.balance, 0) * 2

    @property
    def margin_wallet(self):
        if self.side == SHORT:
            return self.base_margin_wallet
        elif self.side == LONG:
            return self.asset_margin_wallet
        else:
            raise NotImplementedError

    @property
    def margin_vice_versa_wallet(self):
        if self.side == LONG:
            return self.base_margin_wallet
        elif self.side == SHORT:
            return self.asset_margin_wallet
        else:
            raise NotImplementedError

    def get_margin_ratio(self) -> Decimal:
        if self.side == SHORT:
            return 1 / self.DEFAULT_LIQUIDATION_LEVEL
        elif self.side == LONG:
            return self.DEFAULT_LIQUIDATION_LEVEL
        else:
            raise NotImplementedError

    def update_liquidation_price(self, pipeline=None, save: bool = False, rebalance: bool = True):
        if rebalance and self.liquidation_price:
            assert pipeline
            self._rebalance(pipeline)

        debt_amount = self.debt_amount
        total_balance = self.total_balance
        if pipeline:
            debt_amount -= pipeline.get_wallet_balance_diff(self.loan_wallet.id)
            total_balance += pipeline.get_wallet_balance_diff(self.margin_wallet.id)
        if debt_amount and total_balance:
            if self.side == SHORT:
                self.liquidation_price = total_balance / debt_amount / self.DEFAULT_LIQUIDATION_LEVEL
            elif self.side == LONG:
                self.liquidation_price = debt_amount / total_balance * self.DEFAULT_LIQUIDATION_LEVEL
            else:
                raise NotImplementedError
        else:
            self.liquidation_price = None

        if save:
            self.save(update_fields=['liquidation_price'])

    def _rebalance(self, pipeline):
        assert pipeline

        from ledger.models import Wallet

        debt_amount = self.debt_amount
        total_balance = self.total_balance
        if pipeline:
            debt_amount -= pipeline.get_wallet_balance_diff(self.loan_wallet.id)
            total_balance += pipeline.get_wallet_balance_diff(self.margin_wallet.id)

        if total_balance and debt_amount:
            if self.side == SHORT:
                liquidation_price = total_balance / debt_amount / self.DEFAULT_LIQUIDATION_LEVEL
                ratio = Decimal(1 - self.liquidation_price / liquidation_price)
                amount = total_balance * ratio
            elif self.side == LONG:
                liquidation_price = debt_amount / total_balance * self.DEFAULT_LIQUIDATION_LEVEL
                ratio = Decimal(self.liquidation_price / liquidation_price - 1)
                amount = debt_amount * ratio
            else:
                return
        else:
            return

        if amount > Decimal('0'):
            pipeline.new_trx(
                sender=self.base_margin_wallet,
                receiver=self.symbol.base_asset.get_wallet(self.account, Wallet.MARGIN, None),
                amount=amount,
                group_id=uuid.uuid4(),
                scope=Trx.MARGIN_TRANSFER
            )

    @classmethod
    def get_by(cls, symbol: PairSymbol, account: Account, order_side: str, is_open_position: bool):
        assert order_side is not None

        if is_open_position:
            position_side = SHORT if order_side == SELL else LONG
        else:
            position_side = SHORT if order_side == BUY else LONG

        from ledger.models import Wallet
        position = cls.objects.filter(
            account=account,
            symbol=symbol,
            status__in=[cls.OPEN, cls.TERMINATING],
            side=position_side
        ).first()

        if position:
            return position
        else:
            group_id = uuid.uuid5(uuid.NAMESPACE_X500, f'{account.id}-{symbol.name}-{position_side}')
            margin_leverage, _ = MarginLeverage.objects.get_or_create(
                account=account,
                defaults={
                    'leverage': Decimal('1') if position_side == SHORT else Decimal('2')
                }
            )

            return cls.objects.create(
                account=account,
                symbol=symbol,
                status=cls.OPEN,
                group_id=group_id,
                base_wallet=symbol.base_asset.get_wallet(account, Wallet.MARGIN, group_id),
                asset_wallet=symbol.asset.get_wallet(account, Wallet.MARGIN, group_id),
                side=position_side,
                leverage=margin_leverage.leverage
            )

    def has_enough_margin(self, extending_base_amount):
        if self.side == SHORT and self.leverage == 1:
            return self.withdrawable_base_asset >= extending_base_amount
        raise NotImplementedError

    def get_insurance_wallet(self):
        if self.side == SHORT:
            return self.symbol.base_asset.get_wallet(account=Account.objects.get(id=MARGIN_INSURANCE_ACCOUNT))
        elif self.side == LONG:
            return self.symbol.asset.get_wallet(account=Account.objects.get(id=MARGIN_INSURANCE_ACCOUNT))
        else:
            raise NotImplementedError

    def get_margin_pool_wallet(self):
        return self.loan_wallet.asset.get_wallet(account=Account.objects.get(id=MARGIN_POOL_ACCOUNT))

    def get_interest_rate(self):
        from ledger.models import Asset

        if self.loan_wallet.asset.name == Asset.IRT:
            return self.DEFAULT_IRT_INTEREST_FEE_PERCENTAGE
        return self.DEFAULT_USDT_INTEREST_FEE_PERCENTAGE

    def liquidate(self, pipeline, charge_insurance: bool = True):  # todo :: fix
        if self.status != self.OPEN:
            return

        self.status = self.TERMINATING
        self.save(update_fields=['status'])

        from market.utils.order_utils import Order, new_order
        from ledger.models import Trx, Wallet

        Order.cancel_orders(Order.open_objects.filter(wallet__in=[self.base_wallet, self.asset_wallet]))

        loan_wallet_balance_diff = pipeline.get_wallet_balance_diff(self.loan_wallet.id)

        to_close_amount = ceil_precision((self.debt_amount - loan_wallet_balance_diff)
                                         / (1 - self.symbol.get_fee_rate(self.account, is_maker=False)), self.symbol.step_size)
        if self.side == SHORT:
            side = BUY
            price = get_depth_price(symbol=self.symbol.name, side=get_other_side(side), amount=to_close_amount)
        else:
            side = SELL
            price = get_base_depth_price(symbol=self.symbol.name, side=get_other_side(side), amount=to_close_amount)
        free_amount = floor_precision(self.margin_wallet.get_free(), self.symbol.step_size)

        if self.side == SHORT:
            free_amount /= price
        elif self.side == LONG:
            to_close_amount /= price
        else:
            raise NotImplementedError

        loss_amount = max((to_close_amount - free_amount) * Decimal('1.02'), Decimal('0'))
        if self.side == SHORT:
            loss_amount *= price

        group_id = uuid.uuid4()
        if loss_amount > Decimal('0') and self.side:
            pipeline.new_trx(
                self.get_insurance_wallet(),
                self.margin_wallet,
                loss_amount,
                Trx.MARGIN_INSURANCE,
                group_id,
            )
        liquidation_order = None
        if to_close_amount > Decimal('0'):
            liquidation_order = new_order(
                pipeline=pipeline,
                symbol=self.symbol,
                account=self.account,
                amount=ceil_precision(to_close_amount, self.symbol.step_size),
                fill_type=Order.MARKET,
                side=side,
                market=Wallet.MARGIN,
                variant=self.group_id,
                pass_min_notional=True,
                order_type=Order.LIQUIDATION,
                parent_lock_group_id=group_id
            )

        margin_cross_wallet = self.margin_wallet.asset.get_wallet(self.account, market=Wallet.MARGIN, variant=None)
        remaining_balance = self.margin_wallet.balance + pipeline.get_wallet_free_balance_diff(self.margin_wallet.id)

        if remaining_balance > Decimal('0') and loss_amount > Decimal('0'):
            pipeline.new_trx(
                self.margin_wallet,
                self.get_insurance_wallet(),
                min(loss_amount, remaining_balance),
                Trx.MARGIN_INSURANCE,
                group_id,
            )
            remaining_balance -= min(loss_amount, remaining_balance)

        if remaining_balance > Decimal('0'):
            insurance_fee_amount = min(remaining_balance,
                                       to_close_amount * price * self.DEFAULT_INSURANCE_FEE_PERCENTAGE)
            if insurance_fee_amount > Decimal(0) and charge_insurance:
                pipeline.new_trx(
                    self.margin_wallet,
                    self.get_insurance_wallet(),
                    insurance_fee_amount,
                    Trx.LIQUID,
                    group_id
                )
                remaining_balance -= insurance_fee_amount
            if remaining_balance > Decimal(0):
                pipeline.new_trx(
                    self.margin_wallet,
                    margin_cross_wallet,
                    remaining_balance,
                    Trx.LIQUID,
                    group_id
                )
            else:
                logger.warning(f"Negative remaining balance for position:{self.id}")

        if liquidation_order:
            liquidation_order.refresh_from_db()

            if liquidation_order.filled_amount >= to_close_amount:
                self.amount = Decimal(0)
                self.status = self.CLOSED
            else:
                filled_amount = liquidation_order.filled_amount if self.side == SHORT else liquidation_order.filled_amount * liquidation_order.price
                self.amount = max(self.debt_amount - filled_amount, Decimal('0'))
                logger.warning(f'Position:{self.id} doesnt close in Liquidation Process Due to Order'
                               f' filled amount{liquidation_order.filled_amount}/{self.debt_amount}')

            if liquidation_order.filled_amount == Decimal('0') and liquidation_order.status == Order.CANCELED:
                self.status = self.OPEN
        else:
            self.amount = Decimal(0)
            self.status = self.CLOSED

        self.save(update_fields=['amount', 'status'])
        self.update_liquidation_price(pipeline, rebalance=False)

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


class MarginLeverage(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE)
    leverage = get_amount_field(default=Decimal('1'), validators=(MinValueValidator(2),))

    def __str__(self):
        return f'{self.account}-{self.leverage}'


@dataclass
class MarginPositionTradeInfo:
    loan_type: str
    position: MarginPosition
    trade_amount: Decimal = 0
    trade_price: Decimal = 0
    group_id: UUID = 0
