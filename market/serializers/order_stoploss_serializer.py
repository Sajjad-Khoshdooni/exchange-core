import logging
from decimal import Decimal
from typing import Union

from rest_framework import serializers

from ledger.models import Wallet
from ledger.utils.precision import floor_precision
from market.models import Order, StopLoss

logger = logging.getLogger(__name__)


class OrderStopLossSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source='symbol.name')
    id = serializers.SerializerMethodField()
    filled_amount = serializers.SerializerMethodField()
    filled_price = serializers.SerializerMethodField()
    trigger_price = serializers.SerializerMethodField()
    market = serializers.CharField(source='wallet.market', default=Wallet.SPOT)

    def to_representation(self, instance: Union[Order, StopLoss]):
        data = super(OrderStopLossSerializer, self).to_representation(instance)
        data['amount'] = str(floor_precision(Decimal(data['amount']), instance.symbol.step_size))
        data['price'] = str(floor_precision(Decimal(data['price']), instance.symbol.tick_size))
        data['symbol'] = instance.symbol.name
        return data

    def get_id(self, instance: Union[Order, StopLoss]):
        if isinstance(instance, StopLoss):
            return f'sl-{instance.id}'
        return str(instance.id)

    def get_filled_amount(self, instance: Union[Order, StopLoss]):
        return str(floor_precision(instance.filled_amount, instance.symbol.step_size))

    def get_trigger_price(self, instance: Union[Order, StopLoss]):
        if isinstance(instance, Order):
            return None
        return str(floor_precision(instance.trigger_price, instance.symbol.tick_size))

    def get_filled_price(self, instance: Union[Order, StopLoss]):
        order = instance if isinstance(instance, Order) else instance.order_set.first()
        if not order:
            return None
        fills_amount, fills_value = self.context['trades'].get(order.id, (0, 0))
        amount = Decimal((fills_amount or 0))
        if not amount:
            return None
        price = Decimal((fills_value or 0)) / amount
        return str(floor_precision(price, order.symbol.tick_size))

    class Meta:
        model = Order
        fields = ('id', 'created', 'wallet', 'symbol', 'amount', 'filled_amount', 'price', 'filled_price',
                  'trigger_price', 'side', 'fill_type', 'status', 'market')
