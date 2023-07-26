from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from django.db import models

from accounts.models import Account
from ledger.utils.external_price import SHORT, LONG
from ledger.utils.fields import get_amount_field
from market.models import PairSymbol


class MarginPosition(models.Model):
    DEFAULT_LIQUIDATION_LEVEL = Decimal('1.1')

    OPEN, CLOSED = 'open', 'closed'
    STATUS_CHOICES = [(OPEN, OPEN), (CLOSED, CLOSED)]
    SIDE_CHOICES = [(LONG, LONG), (SHORT, SHORT)]

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    wallet = models.OneToOneField('ledger.Wallet', on_delete=models.PROTECT)

    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.PROTECT)
    amount = get_amount_field(default=0)
    average_price = get_amount_field(default=0)
    liquidation_price = get_amount_field(null=True)
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    status = models.CharField(default=OPEN, max_length=8, choices=STATUS_CHOICES)
    leverage = models.IntegerField(default=1)

    @property
    def variant(self):
        return self.wallet.variant

    @property
    def margin_base_wallet(self):
        return self.symbol.base_asset.get_wallet(self.account, self.wallet.MARGIN, self.wallet.variant)

    @property
    def total_balance(self):
        return self.margin_base_wallet.balance

    @property
    def loan_wallet(self):
        return self.symbol.asset.get_wallet(self.account, self.wallet.LOAN, self.wallet.variant)

    @property
    def debt_amount(self):
        return -self.loan_wallet.balance

    @property
    def total_debt(self):
        from ledger.utils.external_price import get_external_price, BUY
        price = get_external_price(self.symbol.asset.symbol, base_coin=self.symbol.base_asset.symbol, side=BUY)
        return self.debt_amount * price

    def update_liquidation_price(self, pipeline=None):
        if self.side == SHORT and self.leverage == 1:
            debt_amount = self.debt_amount
            total_balance = self.total_balance
            print(total_balance)
            if pipeline:
                debt_amount -= pipeline.get_wallet_balance_diff(self.loan_wallet.id)
                total_balance += pipeline.get_wallet_balance_diff(self.margin_base_wallet.id)
            if debt_amount:
                print(total_balance, debt_amount)
                self.liquidation_price = total_balance / (self.DEFAULT_LIQUIDATION_LEVEL * debt_amount)
            else:
                self.liquidation_price = None
        else:
            raise NotImplementedError

    @classmethod
    def get_by(cls, symbol: PairSymbol, account: Account, side=SHORT):
        from ledger.models import Wallet
        position, _ = cls.objects.get_or_create(
            account=account,
            symbol=symbol,
            status=cls.OPEN,
            defaults={
                'wallet': symbol.asset.get_wallet(account, Wallet.MARGIN, uuid4()),
                'side': side
            }
        )
        return position

    def has_enough_margin(self, extending_base_amount):
        # TODO: works fine only with leverage 1
        print('----', self.total_balance - Decimal(2) * self.total_debt, extending_base_amount)
        return self.total_balance - Decimal(2) * self.total_debt >= extending_base_amount


@dataclass
class MarginPositionTradeInfo:
    loan_type: str
    position: MarginPosition
    trade_amount: Decimal = 0
    trade_price: Decimal = 0
