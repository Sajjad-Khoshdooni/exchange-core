from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404

from ledger.exceptions import InsufficientBalance, SmallAmountTrade
from ledger.models import OTCRequest, Asset, OTCTrade
from ledger.models.asset import InvalidAmount
from ledger.models.otc_trade import TokenExpired
from ledger.utils.fields import get_serializer_amount_field


class OTCRequestSerializer(serializers.ModelSerializer):
    from_asset = serializers.CharField(source='from_asset.symbol')
    to_asset = serializers.CharField(source='to_asset.symbol')
    from_amount = get_serializer_amount_field(allow_null=True, required=False)
    to_amount = get_serializer_amount_field(allow_null=True, required=False)
    price = get_serializer_amount_field(source='to_price', read_only=True)
    expire = serializers.SerializerMethodField()

    def validate(self, attrs):
        from_symbol = attrs['from_asset']['symbol']
        to_symbol = attrs['to_asset']['symbol']

        if not {Asset.IRT, Asset.USDT} & {from_symbol, to_symbol}:
            raise ValidationError('یکی از دارایی‌ها باید تومان یا تتر باشد.')

        if from_symbol == to_symbol:
            raise ValidationError('هر دو دارایی نمی‌تواند یکی باشد.')

        try:
            attrs['from_asset'] = Asset.get(from_symbol)
            attrs['to_asset'] = Asset.get(to_symbol)
        except:
            raise ValidationError('دارایی نامعتبر است.')

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
                market=validated_data.get('market'),
            )
        except InvalidAmount as e:
            raise ValidationError(str(e))
        except SmallAmountTrade:
            raise ValidationError('ارزش معامله باید حداقل 100,000 تومان باشد.')
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست.'})

    def get_expire(self, otc: OTCRequest):
        return otc.get_expire_time()

    def to_representation(self, instance: OTCRequest):
        representation = super(OTCRequestSerializer, self).to_representation(instance)

        representation['from_amount'] = instance.from_asset.get_presentation_amount(representation['from_amount'])
        representation['to_amount'] = instance.to_asset.get_presentation_amount(representation['to_amount'])

        return representation

    class Meta:
        model = OTCRequest
        fields = ('from_asset', 'to_asset', 'from_amount', 'to_amount', 'token', 'price', 'expire', 'market')
        read_only_fields = ('token', 'price')


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


class OTCTradeView(CreateAPIView):
    serializer_class = OTCTradeSerializer
