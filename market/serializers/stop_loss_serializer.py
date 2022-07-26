import logging
from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ledger.exceptions import InsufficientBalance
from ledger.models import Wallet
from ledger.utils.precision import floor_precision
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import StopLoss, Order
from market.serializers.order_serializer import OrderSerializer

logger = logging.getLogger(__name__)


class StopLossSerializer(OrderSerializer):
    symbol = serializers.CharField(source='symbol.name')
    filled_amount = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    market = serializers.CharField(source='wallet.market', default=Wallet.SPOT)
    trigger_price = serializers.DecimalField(max_digits=18, decimal_places=0)

    def get_completed(self, stop_loss: StopLoss):
        return stop_loss.filled_amount == stop_loss.amount

    def to_representation(self, stop_loss: StopLoss):
        data = super(OrderSerializer, self).to_representation(stop_loss)
        data['amount'] = str(floor_precision(Decimal(data['amount']), stop_loss.symbol.step_size))
        if data['price']:
            data['price'] = str(floor_precision(Decimal(data['price']), stop_loss.symbol.tick_size))
        data['trigger_price'] = str(floor_precision(Decimal(data['trigger_price']), stop_loss.symbol.tick_size))
        data['symbol'] = stop_loss.symbol.name
        return data

    def create(self, validated_data):
        symbol, wallet = self.post_validate(validated_data)
        if validated_data['price']:
            validated_data['price'] = self.post_validate_price(symbol, validated_data['price'])
        validated_data['trigger_price'] = self.post_validate_price(symbol, validated_data['trigger_price'])
        try:
            with WalletPipeline() as pipeline:
                lock_amount = Order.get_to_lock_amount(
                    validated_data['amount'], validated_data['price'], validated_data['side']
                )
                base_wallet = symbol.base_asset.get_wallet(wallet.account, wallet.market)
                lock_wallet = Order.get_to_lock_wallet(wallet, base_wallet, validated_data['side'])
                if lock_wallet.has_balance(lock_amount, raise_exception=True):
                    instance = super(OrderSerializer, self).create(
                        {**validated_data, 'wallet': wallet, 'symbol': symbol}
                    )
                    instance.acquire_lock(lock_wallet, lock_amount, pipeline)
                    return instance
        except InsufficientBalance:
            raise ValidationError(_('Insufficient Balance'))

    def validate(self, attrs):
        return super(OrderSerializer, self).validate(attrs)

    class Meta:
        model = StopLoss
        fields = ('id', 'created', 'wallet', 'symbol', 'amount', 'filled_amount', 'price', 'trigger_price', 'side',
                  'fill_type', 'completed', 'market', 'canceled_at')
        read_only_fields = ('id', 'created', 'canceled_at')
        extra_kwargs = {
            'wallet': {'write_only': True, 'required': False},
        }
