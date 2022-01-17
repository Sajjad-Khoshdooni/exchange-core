from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404

from ledger.exceptions import InsufficientBalance
from ledger.models import OTCRequest, Asset, OTCTrade
from ledger.models.asset import InvalidAmount
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

        if Asset.IRT not in (from_symbol, to_symbol):
            raise ValidationError('one of from_asset or to_asset should be IRT')

        if from_symbol == to_symbol:
            raise ValidationError('from_asset and to_asset could not be same')

        try:
            attrs['from_asset'] = Asset.get(from_symbol)
            attrs['to_asset'] = Asset.get(to_symbol)
        except:
            raise ValidationError('Invalid from_asset or to_asset')

        from_amount = attrs.get('from_amount')
        to_amount = attrs.get('to_amount')

        if not from_amount and not to_amount:
            raise ValidationError('one amount should present')

        if from_amount and to_amount:
            raise ValidationError('one amount should present')

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        account = request.user.account

        from_asset = validated_data['from_asset']
        to_asset = validated_data['to_asset']

        to_amount = validated_data.get('to_amount')
        from_amount = validated_data.get('from_amount')

        otc_request = OTCRequest(
            account=account,
            from_asset=from_asset,
            to_asset=to_asset,
        )

        try:
            otc_request.set_amounts(from_amount, to_amount)
        except InvalidAmount as e:
            raise ValidationError('%s %s' % (str(e), e.reason))

        conf = otc_request.get_trade_config()
        if conf.cash_amount < 300_000:
            raise ValidationError('small amount!')


        from_wallet = from_asset.get_wallet(account)
        if not from_wallet.can_buy(otc_request.from_amount):
            raise ValidationError({'amount': 'موجودی کافی نیست.'})

        otc_request.save()
        return otc_request

    def get_expire(self, otc: OTCRequest):
        return otc.created + timedelta(seconds=OTCRequest.EXPIRE_TIME)

    class Meta:
        model = OTCRequest
        fields = ('from_asset', 'to_asset', 'from_amount', 'to_amount', 'token', 'price', 'expire')
        read_only_fields = ('token', 'price')


class OTCTradeRequestView(CreateAPIView):
    serializer_class = OTCRequestSerializer


class OTCTradeSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)

    class Meta:
        model = OTCTrade
        fields = ('id', 'token', 'status')

    def create(self, validated_data):
        token = validated_data['token']
        request = self.context['request']

        otc_request = get_object_or_404(OTCRequest, token=token, account=request.user.account)

        otc_trade = OTCTrade.objects.filter(otc_request=otc_request).first()
        if otc_trade:
            return otc_trade

        try:
            return OTCTrade.execute_trade(otc_request)
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست.'})


class OTCTradeView(CreateAPIView):
    serializer_class = OTCTradeSerializer
