import logging
from decimal import Decimal

from django.db import models
from django.utils import timezone

from ledger.models import Wallet
from ledger.utils.fields import get_amount_field, get_price_field, get_lock_field
from ledger.utils.precision import floor_precision

logger = logging.getLogger(__name__)


class StopLossManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.open_only = kwargs.pop('open_only', False)
        super(StopLossManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.open_only:
            return super().get_queryset().filter(deleted_at__isnull=True, completed=False)
        return super().get_queryset().filter(deleted_at__isnull=True)


class StopLoss(models.Model):
    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='stop_losses')
    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.CASCADE)
    amount = get_amount_field()
    filled_amount = get_amount_field(default=Decimal(0))
    price = get_price_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)

    completed = models.BooleanField(default=False)

    lock = get_lock_field(related_name='market_stop_loss')

    deleted_at = models.DateTimeField(blank=True, null=True)

    @property
    def unfilled_amount(self):
        amount = self.amount - self.filled_amount
        return floor_precision(amount, self.symbol.step_size)

    @property
    def base_wallet(self):
        return self.symbol.base_asset.get_wallet(self.wallet.account, self.wallet.market)

    def acquire_lock(self):
        from market.models import Order
        lock_wallet = Order.get_lock_wallet(self.wallet, self.base_wallet, self.side)
        lock_amount = Order.get_lock_amount(self.unfilled_amount, self.price, self.side)
        self.lock = lock_wallet.lock_balance(lock_amount)
        self.save()

    all2_objects = models.Manager()
    objects = StopLossManager()
    open_objects = StopLossManager(open_only=True)

    def save(self, *args, **kwargs):
        if self.filled_amount == self.amount:
            self.completed = True
        return super(StopLoss, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self):
        super(StopLoss, self).delete()
