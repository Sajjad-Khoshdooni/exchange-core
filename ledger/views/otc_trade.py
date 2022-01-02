from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404

from ledger.exceptions import InsufficientBalance
from ledger.models import OTCRequest, Asset, OTCTrade
from ledger.utils.price import get_trading_price


class OTCRequestSerializer(serializers.ModelSerializer):
    coin = serializers.CharField(source='coin.symbol')
    expire = serializers.SerializerMethodField()

    def validate(self, attrs):
        coin_symbol = attrs['coin']['symbol']

        if coin_symbol == Asset.IRT:
            raise ValidationError('coin can not be IRT')

        try:
            attrs['coin'] = Asset.get(coin_symbol)
        except:
            raise ValidationError('Invalid coin')

        return attrs

    def create(self, validated_data):
        request = self.context['request']

        coin = validated_data['coin']
        side = validated_data['side']

        price = get_trading_price(coin.symbol, side)

        return OTCRequest.objects.create(
            account=request.user.account,
            coin=coin,
            side=side,
            price=price
        )

    def get_expire(self, otc: OTCRequest):
        return otc.created + timedelta(seconds=OTCRequest.EXPIRE_TIME)

    class Meta:
        model = OTCRequest
        fields = ('coin', 'side', 'token', 'price', 'expire')
        read_only_fields = ('token', 'price')


class OTCTradeRequestView(CreateAPIView):
    serializer_class = OTCRequestSerializer


class OTCTradeSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)

    class Meta:
        model = OTCTrade
        fields = ('id', 'token', 'amount', 'status')
        read_only_fields = ('id', 'status', )

    def create(self, validated_data):
        token = validated_data['token']
        amount = validated_data['amount']

        request = self.context['request']

        otc_request = get_object_or_404(OTCRequest, token=token, account=request.user.account)

        otc_trade = OTCTrade.objects.filter(otc_request=otc_request).first()
        if otc_trade:
            return otc_trade

        if not otc_request.coin.is_trade_amount_valid(amount):
            raise ValidationError({'amount': 'مقدار نامعتبر است.'})

        try:
            return OTCTrade.create_trade(otc_request, amount)
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست.'})


class OTCTradeView(CreateAPIView):
    serializer_class = OTCTradeSerializer
