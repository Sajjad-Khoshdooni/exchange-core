import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, to_locale, get_language
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import get_object_or_404

from accounts.permissions import can_trade
from ledger.exceptions import InsufficientBalance
from ledger.models import Wallet, Asset, CloseRequest
from ledger.utils.margin import check_margin_view_permission
from ledger.utils.precision import floor_precision, get_precision, humanize_number, get_presentation_amount, \
    decimal_to_str
from ledger.utils.external_price import IRT
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, PairSymbol
from market.utils.redis import MarketStreamCache

logger = logging.getLogger(__name__)


class OrderIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'client_order_id')


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    symbol = serializers.CharField(source='symbol.name')
    filled_amount = serializers.SerializerMethodField()
    filled_percent = serializers.SerializerMethodField()
    filled_price = serializers.SerializerMethodField()
    trigger_price = serializers.SerializerMethodField()
    market = serializers.CharField(source='wallet.market', default=Wallet.SPOT)
    allow_cancel = serializers.SerializerMethodField()

    def to_representation(self, order: Order):
        data = super(OrderSerializer, self).to_representation(order)
        data['amount'] = decimal_to_str(floor_precision(Decimal(data['amount']), order.symbol.step_size))
        data['price'] = decimal_to_str(floor_precision(Decimal(data['price']), order.symbol.tick_size))
        data['symbol'] = order.symbol.name
        return data

    def create(self, validated_data):
        symbol_name = validated_data['symbol']['name'].upper()
        log_prefix = 'CO %s: ' % symbol_name
        logger.info(log_prefix + f' started creating... {timezone.now()}')
        request = self.context['request']

        if not can_trade(request):
            raise ValidationError('در حال حاضر امکان سفارش‌گذاری وجود ندارد.')

        if not settings.MARKET_TRADE_ENABLE and not request.user.account.is_system():
            raise ValidationError('در حال حاضر امکان سفارش‌گذاری وجود ندارد.')

        symbol = get_object_or_404(PairSymbol, name=symbol_name)

        if validated_data['fill_type'] == Order.LIMIT:
            validated_data['price'] = self.post_validate_price(symbol, validated_data['price'])

        elif validated_data['fill_type'] == Order.MARKET:
            validated_data['price'] = Order.get_market_price(symbol, Order.get_opposite_side(validated_data['side']))
            if not validated_data['price']:
                raise Exception('Empty order book')

        wallet = self.post_validate(symbol, validated_data)

        try:
            with WalletPipeline() as pipeline:
                created_order = super(OrderSerializer, self).create(
                    {**validated_data, 'account': wallet.account, 'wallet': wallet, 'symbol': symbol}
                )
                matched_trades = created_order.submit(pipeline)

            extra = {} if matched_trades.trade_pairs else {'side': created_order.side}
            MarketStreamCache().execute(symbol, matched_trades.filled_orders, trade_pairs=matched_trades.trade_pairs, **extra)
            filtered_trades = list(filter(lambda t: t.order_id == created_order.id, matched_trades.trades))
            filled_amount = Decimal(sum(map(lambda t: t.amount, filtered_trades)))
            created_order.filled_amount = filled_amount
            filled_value = Decimal(sum(map(lambda t: t.price * t.amount, filtered_trades)))
            self.context['trades'] = {created_order.id: (filled_amount, filled_value)}

        except InsufficientBalance:
            raise ValidationError(_('Insufficient Balance'))
        except Exception as e:
            logger.error('failed placing order', extra={'exp': e, 'order': validated_data})
            if settings.DEBUG_OR_TESTING_OR_STAGING:
                raise e
            raise APIException(_('Could not place order'))
        logger.info(log_prefix + f' finished creating... {created_order.id} {timezone.now()}')
        return created_order

    def post_validate(self, symbol, validated_data):
        if not symbol.asset.enable:
            raise ValidationError(_('{symbol} is not enable').format(symbol=symbol))
        if not symbol.enable and self.context['account'].id != settings.MARKET_MAKER_ACCOUNT_ID:
            raise ValidationError(_('{symbol} is not enable').format(symbol=symbol))

        market = validated_data.pop('wallet')['market']
        if market == Wallet.MARGIN:
            check_margin_view_permission(self.context['account'], symbol.asset)

            if symbol.base_asset.symbol == Asset.IRT:
                raise ValidationError(_('{symbol} is not enable in margin trading').format(symbol=symbol))

        validated_data['amount'] = self.post_validate_amount(symbol, validated_data['amount'])
        wallet = symbol.asset.get_wallet(self.context['account'], market=market, variant=self.context['variant'])
        min_order_size = Order.MIN_IRT_ORDER_SIZE if symbol.base_asset.symbol == IRT else Order.MIN_USDT_ORDER_SIZE
        self.validate_order_size(
            validated_data['amount'], validated_data['price'], min_order_size, symbol.base_asset.symbol
        )
        return wallet

    @staticmethod
    def post_validate_amount(symbol: PairSymbol, amount: Decimal):
        quantize_amount = floor_precision(Decimal(amount), symbol.step_size)
        if quantize_amount < symbol.min_trade_quantity:
            raise ValidationError(
                {'amount': _('amount is less than {min_quantity} {asset}').format(
                    min_quantity=get_presentation_amount(symbol.min_trade_quantity, symbol.step_size),
                    asset=symbol.asset.symbol
                )}
            )
        if quantize_amount > symbol.max_trade_quantity:
            raise ValidationError(
                {'amount': _('amount is more than {max_quantity} {asset}').format(
                    max_quantity=get_presentation_amount(symbol.max_trade_quantity, symbol.step_size),
                    asset=symbol.asset.symbol
                )}
            )
        return quantize_amount

    @staticmethod
    def validate_order_size(amount: Decimal, price: Decimal, min_order_size: Decimal, base_asset: str):
        if (amount * price) < min_order_size:
            msg = _('Small order size {min_order_size} {base_asset}').format(
                min_order_size=humanize_number(min_order_size),
                base_asset=base_asset
            )
            if to_locale(get_language()) == 'fa_IR':
                msg = msg.replace(Asset.IRT, str(_(Asset.IRT))).replace(Asset.USDT, str(_(Asset.USDT)))

            raise ValidationError({'amount': msg})

    @staticmethod
    def post_validate_price(symbol: PairSymbol, price: Decimal):
        if get_precision(price) > symbol.tick_size:
            raise ValidationError(
                {'price': _('price precision is more than {tick_size}').format(tick_size=symbol.tick_size)}
            )
        return price

    def validate(self, attrs):
        if attrs['fill_type'] == Order.LIMIT and not attrs.get('price'):
            raise ValidationError(
                {'price': _('price is mandatory in limit order.')}
            )
        return attrs

    def get_filled_amount(self, order: Order):
        return decimal_to_str(floor_precision(order.filled_amount, order.symbol.step_size))

    def get_filled_percent(self, order: Order):
        return decimal_to_str(floor_precision(100 * order.filled_amount / order.amount, 0)) + '%'

    def get_id(self, instance: Order):
        if instance.stop_loss:
            return f'sl-{instance.stop_loss_id}'
        return str(instance.id)

    def get_trigger_price(self, instance: Order):
        if instance.stop_loss:
            return decimal_to_str(floor_precision(instance.stop_loss.trigger_price, instance.symbol.tick_size))

    def get_filled_price(self, order: Order):
        fills_amount, fills_value = self.context['trades'].get(order.id, (0, 0))
        amount = Decimal((fills_amount or 0))
        if not amount:
            return None
        price = Decimal((fills_value or 0)) / amount
        return decimal_to_str(floor_precision(price, order.symbol.tick_size))

    def get_allow_cancel(self, instance: Order):
        if instance.wallet.variant:
            return False
        return True

    class Meta:
        model = Order
        fields = ('id', 'created', 'wallet', 'symbol', 'amount', 'filled_amount', 'filled_percent', 'price',
                  'filled_price', 'side', 'fill_type', 'status', 'market', 'trigger_price', 'allow_cancel',
                  'client_order_id')
        read_only_fields = ('id', 'created', 'status')
        extra_kwargs = {
            'wallet': {'write_only': True, 'required': False},
            'price': {'required': False},
        }
