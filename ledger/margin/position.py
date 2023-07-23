from decimal import Decimal

from django.db import models

from accounts.models import Account
from ledger.models import Asset, Wallet
from ledger.utils.external_price import SELL, BUY, SHORT, LONG
from ledger.utils.fields import get_amount_field, get_group_id_field


class MarginPosition(models.Model):
    MARKET_BORDER = Decimal('1e-2')
    MIN_IRT_ORDER_SIZE = Decimal('1e5')
    MIN_USDT_ORDER_SIZE = Decimal(5)
    MAX_ORDER_DEPTH_SIZE_IRT = Decimal('9e7')
    MAX_ORDER_DEPTH_SIZE_USDT = Decimal(2500)
    MAKER_ORDERS_COUNT = 10 if settings.DEBUG_OR_TESTING else 50

    LIMIT, MARKET = 'limit', 'market'
    FILL_TYPE_CHOICES = [(LIMIT, LIMIT), (MARKET, MARKET)]

    TIME_IN_FORCE_OPTIONS = GTC, FOK, IOC = None, 'FOK', 'IOC'

    NEW, CANCELED, FILLED = 'new', 'canceled', 'filled'
    STATUS_CHOICES = [(NEW, NEW), (CANCELED, CANCELED), (FILLED, FILLED)]
    SIDE_CHOICES = [(LONG, LONG), (SHORT, SHORT)]

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='orders')

    Asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    amount = get_amount_field()
    average_price = get_amount_field()
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    status = models.CharField(default=NEW, max_length=8, choices=STATUS_CHOICES)

    group_id = get_group_id_field(null=True)

    client_order_id = models.CharField(max_length=36, null=True, blank=True)

    stop_loss = models.ForeignKey(to='market.StopLoss', on_delete=models.SET_NULL, null=True, blank=True)

    time_in_force = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        choices=[(GTC, 'GTC'), (FOK, 'FOK'), (IOC, 'IOC')]
    )
    login_activity = models.ForeignKey('accounts.LoginActivity', on_delete=models.SET_NULL, null=True, blank=True)

    @classmethod
    def get_by(cls, asset: Asset, account: Account):
        position, _ = cls.objects.get_or_create(

        )

    def has_enough_margin(self, extending_base_amount):
        return self.total_balance - Decimal(2) * self.total_debt >= extending_base_amount
