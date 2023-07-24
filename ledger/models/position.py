from decimal import Decimal
from uuid import uuid4

from django.db import models

from accounts.models import Account
from ledger.utils.external_price import SHORT, LONG
from ledger.utils.fields import get_amount_field
from market.models import PairSymbol


class MarginPosition(models.Model):
    OPEN, CLOSED = 'open', 'closed'
    STATUS_CHOICES = [(OPEN, OPEN), (CLOSED, CLOSED)]
    SIDE_CHOICES = [(LONG, LONG), (SHORT, SHORT)]

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    wallet = models.OneToOneField('ledger.Wallet', on_delete=models.PROTECT)

    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.PROTECT)
    amount = get_amount_field(default=0)
    average_price = get_amount_field(default=0)
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    status = models.CharField(default=OPEN, max_length=8, choices=STATUS_CHOICES)
    leverage = models.IntegerField(default=1)

    @property
    def variant(self):
        return self.wallet.variant

    @property
    def total_balance(self):
        from ledger.models import Wallet
        from ledger.utils.external_price import get_external_price, BUY
        price = get_external_price(self.symbol.asset.symbol, base_coin=self.symbol.base_asset.symbol, side=BUY)
        return self.wallet.balance * price + \
            self.symbol.asset.get_wallet(self.account, Wallet.LOAN, self.wallet.variant).balance * price + \
            self.symbol.base_asset.get_wallet(self.account, Wallet.MARGIN, self.wallet.variant).balance

    @property
    def total_debt(self):
        from ledger.models import Wallet
        from ledger.utils.external_price import get_external_price, BUY
        price = get_external_price(self.symbol.asset.symbol, base_coin=self.symbol.base_asset.symbol, side=BUY)
        return self.symbol.asset.get_wallet(self.account, Wallet.LOAN, self.wallet.variant).balance * price

    @classmethod
    def get_by(cls, symbol: PairSymbol, account: Account, side=SHORT):
        from ledger.models import Wallet
        position, _ = cls.objects.get_or_create(
            account=account,
            symbol=symbol,
            defaults={
                'wallet': symbol.asset.get_wallet(account, Wallet.MARGIN, uuid4()),
                'side': side
            }
        )
        return position

    def has_enough_margin(self, extending_base_amount):
        # TODO: works fine only with leverage 1
        return self.total_balance - Decimal(2) * self.total_debt >= extending_base_amount
