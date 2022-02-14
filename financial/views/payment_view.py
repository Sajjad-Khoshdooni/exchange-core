from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404

from accounts.permissions import IsBasicVerified
from financial.models import BankCard, PaymentRequest


class PaymentRequestSerializer(serializers.ModelSerializer):
    callback = serializers.SerializerMethodField(read_only=True)

    def get_callback(self, payment_request: PaymentRequest):
        return payment_request.get_gateway().get_redirect_url(payment_request)

    def create(self, validated_data):
        amount = validated_data['amount']
        card_pan = validated_data['card_pan']

        bank_card = get_object_or_404(BankCard, card_pan=card_pan)

        if not bank_card.verified:
            raise ValidationError({'card_pan': 'شماره کارت تایید نشده است.'})

        from financial.models import Gateway
        gateway = Gateway.get_active()
        return gateway.create_payment_request(bank_card=bank_card, amount=amount)

    class Meta:
        model = PaymentRequest
        fields = ('callback', 'amount', 'card_pan')


class PaymentRequestView(CreateAPIView):
    permission_classes = (IsBasicVerified, )
    serializer_class = PaymentRequestSerializer
