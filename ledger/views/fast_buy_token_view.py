from rest_framework import serializers
from rest_framework.generics import CreateAPIView

from financial.models import PaymentRequest
from financial.views.payment_view import PaymentRequestSerializer
from ledger.models import Asset
from ledger.models.asset import CoinField
from ledger.models.fast_by_token import FastBuyToken


class FastBuyTokenSerializer(serializers.ModelSerializer):
    coin = CoinField(source='asset')
    card_pan = serializers.CharField(write_only=True)
    callback = serializers.SerializerMethodField(read_only=True)

    def get_call_back(self, asf: PaymentRequest):
        pass

    def create(self, validated_data):

        validated_data['payment_request'] = PaymentRequestSerializer.create(validated_data)

        super().create(validated_data)

    class Meta:
        model = FastBuyToken
        fields = ('coin', 'fiat_amount', )


class FastBuyTokenAPI(CreateAPIView):
    serializer_class = FastBuyTokenSerializer
    queryset = FastBuyToken.objects.all()

