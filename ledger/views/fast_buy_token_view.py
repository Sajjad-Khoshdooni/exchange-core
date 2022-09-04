from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.views.authentication import CustomTokenAuthentication
from financial.models import PaymentRequest, BankCard
from financial.views.payment_view import PaymentRequestSerializer
from ledger.models import Asset
from ledger.models.asset import CoinField
from ledger.models.fast_buy_token import FastBuyToken
from ledger.utils.price import get_price


class FastBuyTokenSerializer(serializers.ModelSerializer):
    coin = CoinField(source='asset')
    bank_card_id = serializers.IntegerField(source='payment_request.bank_card_id')
    callback = serializers.SerializerMethodField(read_only=True)

    def get_callback(self, fast_buy_token: FastBuyToken):
        payment_request = fast_buy_token.payment_request
        return payment_request.get_gateway().get_initial_redirect_url(payment_request)

    def validate(self, attrs):
        if attrs['amount'] < FastBuyToken.MIN_ADMISSIBLE_VALUE:
            raise ValidationError('حداقل مقدار سفارش 300 هزار تومان است.')
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        payment_request_serializer = PaymentRequestSerializer()
        payment_request_serializer.context['request'] = request
        card_pan = BankCard.objects.get(id=validated_data['payment_request']['bank_card_id']).card_pan
        validated_data['card_pan'] = card_pan
        validated_data['payment_request'] = payment_request_serializer.create(validated_data)
        validated_data['user'] = request.user
        validated_data.pop('card_pan')
        validated_data['price'] = get_price(coin=validated_data['asset'].symbol, side='sell') or 0
        return super().create(validated_data)

    class Meta:
        model = FastBuyToken
        fields = ('coin', 'amount', 'bank_card_id', 'callback')


class FastBuyTokenAPI(CreateAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    serializer_class = FastBuyTokenSerializer
    queryset = FastBuyToken.objects.all()

