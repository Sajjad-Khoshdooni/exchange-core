from decimal import Decimal, InvalidOperation

from django.conf import settings
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

        if from_amount and to_amount:
            raise ValidationError({'amount': 'دقیقا یکی از این مقدایر می‌تواند پر باشد.'})

        if not from_amount and not to_amount:
            if from_asset.symbol in (Asset.IRT, Asset.USDT):
                from_amount = 1
            else:
                to_amount = 1

        otc = OTCRequest.get_otc_request(
            account=self.request.user.account,
            from_asset=from_asset,
            to_asset=to_asset,
            from_amount=from_amount and Decimal(from_amount),
            to_amount=to_amount and Decimal(to_amount),
        )

        return Response({
            'base_asset': otc.symbol.base_asset.symbol,
            'asset': otc.symbol.asset.symbol,
            'side': otc.side,
            'price': otc.price,
        })


class OTCRequestSerializer(serializers.ModelSerializer):
    from_asset = serializers.CharField(source='from_asset.symbol')
    to_asset = serializers.CharField(source='to_asset.symbol')
    from_amount = get_serializer_amount_field(allow_null=True, required=False, write_only=True)
    to_amount = get_serializer_amount_field(allow_null=True, required=False, write_only=True)

    paying_amount = serializers.SerializerMethodField()
    receiving_amount = serializers.SerializerMethodField()
    net_receiving_amount = serializers.SerializerMethodField()

    expire = serializers.SerializerMethodField()
    price = get_serializer_amount_field(read_only=True)
    asset = serializers.CharField(source='symbol.asset.symbol', read_only=True)
    base_asset = serializers.CharField(source='symbol.base_asset.symbol', read_only=True)
    fee = get_serializer_amount_field(source='fee_amount', read_only=True)

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

    def get_paying_amount(self, otc_request: OTCRequest) -> Decimal:
        return otc_request.get_paying_amount()

    def get_receiving_amount(self, otc_request: OTCRequest) -> Decimal:
        return otc_request.get_receiving_amount()

    def get_net_receiving_amount(self, otc_request: OTCRequest) -> Decimal:
        return otc_request.get_net_receiving_amount()

    class Meta:
        model = OTCRequest
        fields = ('from_asset', 'to_asset', 'from_amount', 'to_amount',
                  'token', 'expire', 'price', 'asset', 'base_asset', 'paying_amount', 'receiving_amount',
                  'net_receiving_amount', 'fee')


class OTCTradeRequestView(CreateAPIView):
    serializer_class = OTCRequestSerializer


class OTCTradeSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)

    class Meta:
        model = OTCTrade
        fields = ('id', 'token', 'status')
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
