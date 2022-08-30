from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.views.authentication import CustomTokenAuthentication
from financial.models import PaymentRequest
from financial.views.payment_view import PaymentRequestSerializer
from ledger.models import Asset
from ledger.models.asset import CoinField
from ledger.models.fast_buy_token import FastBuyToken
from ledger.utils.price import get_price


class FastBuyTokenSerializer(serializers.ModelSerializer):
    coin = CoinField(source='asset')
    card_pan = serializers.CharField(write_only=True)
    call_back = serializers.SerializerMethodField(read_only=True)

    def get_call_back(self, fast_buy_token: FastBuyToken):
        payment_request = fast_buy_token.payment_request
        return payment_request.get_gateway().get_initial_redirect_url(payment_request)

    def validate(self, attrs):
        if attrs['amount'] < 300000:
            raise ValidationError('حداقل مقدار سفارش 300 هزار تومان است.')
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        payment_request_serializer = PaymentRequestSerializer()
        payment_request_serializer.context['request'] = request
        validated_data['payment_request'] = payment_request_serializer.create(validated_data)
        validated_data['user'] = request.user
        validated_data.pop('card_pan')
        validated_data['price'] = get_price(coin=validated_data['asset'].symbol, side='sell') or 0
        return super().create(validated_data)

    class Meta:
        model = FastBuyToken
        fields = ('coin', 'amount', 'card_pan', 'call_back')


class FastBuyTokenAPI(CreateAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    serializer_class = FastBuyTokenSerializer
    queryset = FastBuyToken.objects.all()

