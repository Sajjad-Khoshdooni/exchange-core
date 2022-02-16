import logging
from decimal import Decimal

from django.db import models

from ledger.models import Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.price import BUY, SELL
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class ProviderHedgedOrder(models.Model):
    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    created = models.DateTimeField(auto_now_add=True)

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    amount = get_amount_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)  # spot side

    caller_id = models.PositiveIntegerField(null=True, blank=True)

    spot_order = models.OneToOneField(to=ProviderOrder, on_delete=models.PROTECT)
    hedged = models.BooleanField(default=False)

    @classmethod
    def new_hedged_order(cls, asset: Asset, amount: Decimal, spot_side: str, caller_id: str) -> 'ProviderHedgedOrder':
        if ProviderHedgedOrder.objects.filter(caller_id=caller_id).exists():
            logger.warning('transfer ignored due to duplicated caller_id')
            return

        spot_order = ProviderOrder.new_order(asset, spot_side, amount, scope=ProviderOrder.WITHDRAW,
                                             market=ProviderOrder.SPOT)

        hedge_order = ProviderHedgedOrder.objects.create(
            asset=asset,
            amount=amount,
            side=spot_side,
            spot_order=spot_order
        )

        future_side = BUY if spot_side == SELL else SELL

        hedge = ProviderOrder.try_hedge_for_new_order(asset, future_side, amount, scope=ProviderOrder.WITHDRAW)

        if not hedge:
            logger.error('failed to hedge HedgedOrder in future')
            return

        hedge_order.hedged = True
        hedge_order.save()

        return hedge_order
