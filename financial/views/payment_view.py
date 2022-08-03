from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from accounts.permissions import IsBasicVerified
from financial.models import BankCard, PaymentRequest, Payment
from financial.models.bank_card import BankCardSerializer
from financial.models.gateway import GatewayFailed


class PaymentRequestSerializer(serializers.ModelSerializer):
    callback = serializers.SerializerMethodField(read_only=True)
    card_pan = serializers.CharField(write_only=True)

    def get_callback(self, payment_request: PaymentRequest):
        return payment_request.get_gateway().get_initial_redirect_url(payment_request)

    def create(self, validated_data):
        amount = validated_data['amount']
        card_pan = validated_data['card_pan']

        user = self.context['request'].user
        bank_card = get_object_or_404(BankCard, card_pan=card_pan, user=user, deleted=False)

        if not bank_card.verified:
            raise ValidationError({'card_pan': 'شماره کارت تایید نشده است.'})

        from financial.models import Gateway
        gateway = Gateway.get_active(user)

        try:
            return gateway.create_payment_request(bank_card=bank_card, amount=amount)
        except GatewayFailed:
            raise ValidationError('مشکلی در ارتباط با درگاه بانک به وجود آمد.')

    class Meta:
        model = PaymentRequest
        fields = ('callback', 'amount', 'card_pan', 'source')


class PaymentRequestView(CreateAPIView):
    queryset = PaymentRequest.objects.all()
    permission_classes = (IsBasicVerified, )
    serializer_class = PaymentRequestSerializer


class PaymentHistorySerializer(serializers.ModelSerializer):

    amount = serializers.IntegerField(source='payment_request.amount')
    bank_card = BankCardSerializer(source='payment_request.bank_card')

    class Meta:
        model = Payment
        fields = ('created', 'status', 'ref_id', 'amount', 'bank_card')


class PaymentHistoryView(ListAPIView):
    serializer_class = PaymentHistorySerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        return Payment.objects.filter(payment_request__bank_card__user=self.request.user).order_by('-created')
