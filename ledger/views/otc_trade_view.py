from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.exceptions import InsufficientBalance, SmallAmountTrade, AbruptDecrease, HedgeError
from ledger.models import OTCRequest, Asset, OTCTrade, Wallet
from ledger.models.asset import InvalidAmount
from ledger.models.otc_trade import TokenExpired
from ledger.utils.fields import get_serializer_amount_field
from ledger.utils.price import SELL, get_tether_irt_price
from market.models.pair_symbol import DEFAULT_TAKER_FEE


class OTCInfoView(APIView):

    def get(self, request: Request):
        from_symbol = request.query_params.get('from')
        to_symbol = request.query_params.get('to')

        try:
            from_amount = request.query_params.get('from_amount')
            from_amount = from_amount and Decimal(from_amount)

            to_amount = request.query_params.get('to_amount')
            to_amount = to_amount and Decimal(to_amount)
        except InvalidOperation:
            raise ValidationError({
                'amount': 'مقدار نامعتبر است.'
            })

        from_asset = get_object_or_404(Asset, symbol=from_symbol)
        to_asset = get_object_or_404(Asset, symbol=to_symbol)

        otc = OTCRequest(
            from_asset=from_asset,
            to_asset=to_asset,
            from_amount=from_amount,
            to_amount=to_amount,
        )

        if from_amount and to_amount:
            raise ValidationError({'amount': 'دقیقا یکی از این مقدایر می‌تواند پر باشد.'})

        if from_amount or to_amount:
            otc.set_amounts(from_amount=from_amount, to_amount=to_amount)

        to_price = otc.get_to_price()
        config = otc.get_trade_config()

        return Response({
            'from': from_symbol,
            'to': to_symbol,
            'cash': config.cash.symbol,
            'coin': config.coin.symbol,
            'side': config.side,
            'to_price': to_price,
            'coin_price': self.get_coin_price(config, to_price)
        })

    def get_coin_price(self, conf, to_price):

        if conf.side == SELL:
            to_price = 1 / to_price

        if conf.cash.symbol == Asset.IRT:
            return conf.coin.get_presentation_price_irt(to_price)
        else:
            return conf.coin.get_presentation_price_usdt(to_price)


class OTCRequestSerializer(serializers.ModelSerializer):
    from_asset = serializers.CharField(source='from_asset.symbol')
    to_asset = serializers.CharField(source='to_asset.symbol')
    from_amount = get_serializer_amount_field(allow_null=True, required=False)
    to_amount = get_serializer_amount_field(allow_null=True, required=False)
    price = get_serializer_amount_field(source='to_price', read_only=True)
    expire = serializers.SerializerMethodField()
    coin = serializers.SerializerMethodField()
    coin_price = serializers.SerializerMethodField()
    cash = serializers.SerializerMethodField()
    fee = serializers.SerializerMethodField()

    def validate(self, attrs):
        from_symbol = attrs['from_asset']['symbol']
        to_symbol = attrs['to_asset']['symbol']

        if not {Asset.IRT, Asset.USDT} & {from_symbol, to_symbol}:
            raise ValidationError('یکی از دارایی‌ها باید تومان یا تتر باشد.')

        if from_symbol == to_symbol:
            raise ValidationError('هر دو دارایی نمی‌تواند یکی باشد.')

        try:
            from_asset = attrs['from_asset'] = Asset.get(from_symbol)
            to_asset = attrs['to_asset'] = Asset.get(to_symbol)
        except:
            raise ValidationError('دارایی نامعتبر است.')

        if not from_asset.trade_enable or not to_asset.trade_enable:
            raise ValidationError('در حال حاضر امکان معامله این رمزارز وجود ندارد.')

        from_amount = attrs.get('from_amount')
        to_amount = attrs.get('to_amount')

        if not from_amount and not to_amount:
            raise ValidationError('یک مقدار باید وارد شود.')

        if from_amount and to_amount:
            raise ValidationError('یک مقدار باید وارد شود.')

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        account = request.user.account

        if not settings.TRADE_ENABLE or not account.user.can_trade:
            raise ValidationError('در حال حاضر امکان معامله وجود ندارد.')

        from_asset = validated_data['from_asset']
        to_asset = validated_data['to_asset']

        to_amount = validated_data.get('to_amount')
        from_amount = validated_data.get('from_amount')

        try:
            return OTCRequest.new_trade(
                account=account,
                from_asset=from_asset,
                to_asset=to_asset,
                from_amount=from_amount,
                to_amount=to_amount,
                market=Wallet.SPOT,
            )
        except InvalidAmount as e:
            raise ValidationError(str(e))
        except SmallAmountTrade:
            raise ValidationError('ارزش معامله باید حداقل ۱۰,۰۰۰ تومان باشد.')
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست.'})

    def get_expire(self, otc: OTCRequest):
        return otc.get_expire_time()

    def to_representation(self, instance: OTCRequest):
        representation = super(OTCRequestSerializer, self).to_representation(instance)

        representation['from_amount'] = instance.from_asset.get_presentation_amount(representation['from_amount'])
        representation['to_amount'] = instance.to_asset.get_presentation_amount(representation['to_amount'])

        return representation

    def get_coin(self, otc_request: OTCRequest):
        conf = otc_request.get_trade_config()
        return conf.coin.symbol

    def get_cash(self, otc_request: OTCRequest):
        conf = otc_request.get_trade_config()
        return conf.cash.symbol

    def get_fee(self, otc_request: OTCRequest) -> Decimal:
        voucher = otc_request.account.get_voucher_wallet()
        if voucher:
            return Decimal(0)
        else:
            return DEFAULT_TAKER_FEE

    def get_coin_price(self, otc_request: OTCRequest):
        conf = otc_request.get_trade_config()

        price = otc_request.to_price

        if conf.side == SELL:
            price = 1 / price

        if conf.cash.symbol == Asset.IRT:
            return conf.coin.get_presentation_price_irt(price)
        else:
            return conf.coin.get_presentation_price_usdt(price)

    class Meta:
        model = OTCRequest
        fields = ('from_asset', 'to_asset', 'from_amount', 'to_amount', 'token', 'price', 'expire', 'coin',
                  'coin_price', 'cash', 'fee')
        read_only_fields = ('token', 'price')


class OTCTradeRequestView(CreateAPIView):
    serializer_class = OTCRequestSerializer


class OTCTradeSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    value_usdt = serializers.SerializerMethodField()

    def get_value_usdt(self, otc_trade: OTCTrade):
        from market.models import Trade
        revenue_irt = Trade.objects.filter(
            group_id=otc_trade.group_id
        ).aggregate(revenue=Sum('gap_revenue'))['revenue'] or 0

        usdt_price = get_tether_irt_price(SELL, allow_stale=True)

        return revenue_irt / usdt_price or 0

    class Meta:
        model = OTCTrade
        fields = ('id', 'token', 'status', 'value_usdt')
        read_only_fields = ('token', )

    def create(self, validated_data):
        token = validated_data['token']
        request = self.context['request']

        if not settings.TRADE_ENABLE or not request.user.can_trade:
            raise ValidationError('در حال حاضر امکان معامله وجود ندارد.')

        otc_request = get_object_or_404(OTCRequest, token=token, account=request.user.account)

        otc_trade = OTCTrade.objects.filter(otc_request=otc_request).first()
        if otc_trade:
            return otc_trade

        try:
            return OTCTrade.execute_trade(otc_request)
        except TokenExpired:
            raise ValidationError({'token': 'سفارش منقضی شده است. لطفا دوباره اقدام کنید.'})
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست.'})
        except InvalidAmount as e:
            raise ValidationError(str(e))
        except AbruptDecrease as e:
            raise ValidationError('مشکلی در ثبت سفارش رخ داد. لطفا دوباره تلاش کنید.')
        except HedgeError as e:
            raise ValidationError('مشکلی در پردازش سفارش رخ داد.')


class OTCTradeView(CreateAPIView):
    serializer_class = OTCTradeSerializer
