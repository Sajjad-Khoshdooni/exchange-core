import logging
from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ledger.exceptions import InsufficientBalance
from ledger.models import Wallet
from ledger.utils.precision import floor_precision
from market.models import StopLoss
from market.serializers.order_serializer import OrderSerializer

logger = logging.getLogger(__name__)


class StopLossSerializer(OrderSerializer):
    symbol = serializers.CharField(source='symbol.name')
    filled_amount = serializers.SerializerMethodField()
    market = serializers.CharField(source='wallet.market', default=Wallet.SPOT)

    def to_representation(self, stop_loss: StopLoss):
        data = super(OrderSerializer, self).to_representation(stop_loss)
        data['amount'] = str(floor_precision(Decimal(data['amount']), stop_loss.symbol.step_size))
        data['price'] = str(floor_precision(Decimal(data['price']), stop_loss.symbol.tick_size))
        data['symbol'] = stop_loss.symbol.name
        return data

    def create(self, validated_data):
        symbol, wallet = self.post_validate(validated_data)
        validated_data['price'] = self.post_validate_price(symbol, validated_data['price'])
        try:
            with transaction.atomic():
                instance = super(OrderSerializer, self).create(
                    {**validated_data, 'wallet': wallet, 'symbol': symbol}
                )
                instance.acquire_lock()
                return instance
        except InsufficientBalance:
            raise ValidationError(_('Insufficient Balance'))

    def validate(self, attrs):
        return super(OrderSerializer, self).validate(attrs)

    class Meta:
        model = StopLoss
        fields = ('id', 'created', 'wallet', 'symbol', 'amount', 'filled_amount', 'price', 'side', 'completed',
                  'market')
        read_only_fields = ('id', 'created', 'completed',)
        extra_kwargs = {
            'wallet': {'write_only': True, 'required': False},
        }
