import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import get_object_or_404

from ledger.exceptions import InsufficientBalance
from ledger.models import Wallet
from ledger.utils.precision import floor_precision, get_precision, get_presentation_amount
from ledger.utils.price import IRT
from market.models import Order, PairSymbol

logger = logging.getLogger(__name__)


class OrderSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source='symbol.name')
    filled_amount = serializers.SerializerMethodField()
    filled_price = serializers.SerializerMethodField()

    def to_representation(self, order: Order):
        data = super(OrderSerializer, self).to_representation(order)
        data['amount'] = str(get_presentation_amount(Decimal(data['amount']), order.symbol.step_size))
        data['price'] = str(get_presentation_amount(Decimal(data['price']), order.symbol.tick_size))
        data['symbol'] = order.symbol.name
        return data

    def create(self, validated_data):
        symbol = get_object_or_404(PairSymbol, name=validated_data['symbol']['name'].upper())
        if not symbol.enable:
            raise ValidationError(f'{symbol} is not enable')

        validated_data['amount'] = self.post_validate_amount(symbol, validated_data['amount'])
        validated_data['price'] = self.post_validate_price(symbol, validated_data['price'])

        wallet = symbol.asset.get_wallet(self.context['account'], market=self.context.get('market', Wallet.SPOT))
        min_order_size = Order.MIN_IRT_ORDER_SIZE if symbol.base_asset.symbol == IRT else Order.MIN_USDT_ORDER_SIZE
        self.validate_order_size(validated_data['amount'], validated_data['price'], min_order_size)

        try:
            with transaction.atomic():
                created_order = super(OrderSerializer, self).create(
                    {**validated_data, 'wallet': wallet, 'symbol': symbol}
                )
                Order.submit(order=created_order)
        except InsufficientBalance:
            raise ValidationError(_('Insufficient Balance'))
        except Exception as e:
            logger.error('failed placing order', extra={'exp': e, 'order': validated_data})
            if settings.DEBUG:
                raise e
            raise APIException(_('Could not place order'))

        return created_order

    @staticmethod
    def post_validate_amount(symbol: PairSymbol, amount: Decimal):
        quantize_amount = floor_precision(Decimal(amount), symbol.step_size)
        if quantize_amount < symbol.min_trade_quantity:
            raise ValidationError(
                {'amount': _('amount is less than {min_quantity}').format(min_quantity=symbol.min_trade_quantity)}
            )
        if quantize_amount > symbol.max_trade_quantity:
            raise ValidationError(
                {'amount': _('amount is more than {max_quantity}').format(max_quantity=symbol.max_trade_quantity)}
            )
        return quantize_amount

    @staticmethod
    def validate_order_size(amount: Decimal, price: Decimal, min_order_size: Decimal):
        if (amount * price) < min_order_size:
            raise ValidationError({'amount': _('Small order size')})

    @staticmethod
    def post_validate_price(symbol: PairSymbol, price: Decimal):
        if get_precision(price) > symbol.tick_size:
            raise ValidationError(
                {'price': _('price precision is more than {tick_size}').format(tick_size=symbol.tick_size)}
            )
        return price

    def get_filled_amount(self, order: Order):
        return get_presentation_amount(order.filled_amount)

    def get_filled_price(self, order: Order):
        filled_price = order.filled_price
        if filled_price is None:
            return None
        return get_presentation_amount(filled_price)

    class Meta:
        model = Order
        fields = ('id', 'created', 'wallet', 'symbol', 'amount', 'filled_amount', 'price', 'filled_price', 'side',
                  'fill_type', 'status')
        read_only_fields = ('id', 'created', 'status',)
        extra_kwargs = {
            'wallet': {'write_only': True, 'required': False}
        }
