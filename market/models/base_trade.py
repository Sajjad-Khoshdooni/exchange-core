import logging
from decimal import Decimal

from django.db import models

from ledger.models import Wallet
from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


class BaseTrade(models.Model):
    BUY, SELL = 'buy', 'sell'
    SIDE_CHOICES = [(BUY, BUY), (SELL, SELL)]

    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    amount = get_amount_field()
    price = get_amount_field()
    is_maker = models.BooleanField()

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.CASCADE)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)

    market = models.CharField(
        max_length=8,
        choices=Wallet.MARKET_CHOICES,
    )
    base_irt_price = get_amount_field()
    base_usdt_price = get_amount_field(default=Decimal(1))

    class Meta:
        abstract = True
