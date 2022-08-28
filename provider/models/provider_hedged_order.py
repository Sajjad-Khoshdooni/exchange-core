import logging
from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q

from ledger.models import Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.price import BUY, SELL, get_price
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class ProviderHedgedOrder(models.Model):
    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    created = models.DateTimeField(auto_now_add=True)

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    amount = get_amount_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)  # spot side

    caller_id = models.CharField(blank=True, null=True, unique=True, max_length=32)

    spot_order = models.OneToOneField(to=ProviderOrder, on_delete=models.PROTECT)
    hedged = models.BooleanField(default=False)

    @classmethod
    def new_hedged_order(cls, asset: Asset, amount: Decimal, spot_side: str, caller_id: str) -> 'ProviderHedgedOrder':
        if ProviderHedgedOrder.objects.filter(caller_id=str(caller_id)).exists():
            logger.warning('hedge order ignored due to duplicated caller_id')
            return

        valid_amount = cls.get_min_trade_amount_to_buy(asset, amount)

        spot_order = ProviderOrder.new_order(asset, spot_side, valid_amount, scope=ProviderOrder.WITHDRAW,
                                             market=ProviderOrder.SPOT)

        hedge_order = ProviderHedgedOrder.objects.create(
            asset=asset,
            amount=valid_amount,
            side=spot_side,
            spot_order=spot_order,
            caller_id=caller_id
        )

        future_side = BUY if spot_side == SELL else SELL

        if asset.hedge_method == Asset.HEDGE_BINANCE_FUTURE:
            hedge = ProviderOrder.try_hedge_for_new_order(asset=asset, side=future_side, scope=ProviderOrder.WITHDRAW)
        else:
            hedge = True

        if not hedge:
            logger.error('failed to hedge HedgedOrder in future')
            return

        hedge_order.hedged = True
        hedge_order.save()

        return hedge_order

    @classmethod
    def get_min_trade_amount_to_buy(cls, asset: Asset, amount: Decimal):
        price = get_price(asset.symbol, BUY)

        handler = asset.get_hedger()
        symbol = handler.get_trading_symbol(asset.symbol)

        min_notional_amount = handler.get_min_notional() / price * Decimal('1.002')

        min_amount = max(amount, min_notional_amount, handler.get_lot_min_quantity(symbol))
        step_size = handler.get_step_size(symbol)

        reminder = min_amount % step_size

        if reminder == 0:
            return min_amount
        else:
            return min_amount + step_size - reminder

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_provider_hedged_order_amount', ), ]
