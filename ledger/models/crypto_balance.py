import logging
from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q
from yekta_config.config import config

from accounts.models import Account
from ledger.consts import DEFAULT_COIN_OF_NETWORK
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_trading_price_usdt, BUY

logger = logging.getLogger(__name__)


class CryptoBalance(models.Model):
    amount = get_amount_field(default=Decimal(0))
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_ledger_crypto_balance_amount', ), ]

    def __str__(self):
        return '%s %s %f' % (self.asset, self.deposit_address, self.amount)

    def get_value(self):
        return self.amount * get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)
