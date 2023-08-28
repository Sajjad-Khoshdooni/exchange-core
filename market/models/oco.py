import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models
from django.db.models import F, CheckConstraint, Q
from django.utils import timezone

from ledger.models import Wallet
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import floor_precision
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class OCOManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(canceled_at__isnull=True)


class OCO(models.Model):
    NEW = 'new'
    TRIGGERED = 'triggered'
    FILLED = 'filled'
    BUY, SELL = 'buy', 'sell'
    SIDE_CHOICES = [(BUY, BUY), (SELL, SELL)]

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='oco_set')
    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.PROTECT)
    amount = get_amount_field()
    releasable_lock = get_amount_field()
    stop_loss_price = get_amount_field()
    stop_loss_trigger_price = get_amount_field()
    price = get_amount_field(null=True)
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)

    canceled_at = models.DateTimeField(blank=True, null=True)

    group_id = models.UUIDField(default=uuid4)

    login_activity = models.ForeignKey('accounts.LoginActivity', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def filled_amount(self):
        order = self.order_set.first()
        if order.filled_amount:
            return order.filled_amount
        if hasattr(self, 'stoploss'):
            return self.stoploss.filled_amount
        return Decimal(0)


    @property
    def unfilled_amount(self):
        amount = self.amount - self.filled_amount
        return floor_precision(amount, self.symbol.step_size)

    @property
    def base_wallet(self):
        return self.symbol.base_asset.get_wallet(
            self.wallet.account, self.wallet.market, variant=self.wallet.variant
        )

    def acquire_lock(self, lock_wallet, lock_amount, pipeline: WalletPipeline):
        pipeline.new_lock(key=self.group_id, wallet=lock_wallet, amount=lock_amount, reason=WalletPipeline.TRADE)

    objects = models.Manager()
    open_objects = OCOManager()

    def delete(self, *args, **kwargs):
        self.canceled_at = timezone.now()
        self.save(update_fields=['canceled_at'])

    def hard_delete(self):
        super(OCO, self).delete()

    class Meta:
        # todo: add constraint filled_amount <= amount
        constraints = [
            CheckConstraint(check=Q(
                amount__gte=0,
                price__gte=0,
            ), name='check_market_OCO_amounts', ),
        ]
