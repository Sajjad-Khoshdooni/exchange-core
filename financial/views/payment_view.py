from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from accounts.models import LoginActivity
from accounts.permissions import IsBasicVerified
from financial.models import BankCard, PaymentRequest, Payment
from financial.models.bank_card import BankCardSerializer
from financial.models.gateway import GatewayFailed
from financial.utils.bank import get_bank_from_iban
from ledger.utils.precision import humanize_number


class PaymentRequestSerializer(serializers.ModelSerializer):
    callback = serializers.SerializerMethodField(read_only=True)
    card_pan = serializers.CharField(write_only=True)

    def get_callback(self, payment_request: PaymentRequest):
        return payment_request.get_gateway().get_initial_redirect_url(payment_request)

    def create(self, validated_data):
        amount = validated_data['amount']
        card_pan = validated_data['card_pan']
        source = validated_data.get('source', PaymentRequest.DESKTOP)

        user = self.context['request'].user
        bank_card = get_object_or_404(BankCard, card_pan=card_pan, user=user, verified=True, deleted=False)

        if not bank_card.verified:
            raise ValidationError({'card_pan': 'شماره کارت تایید نشده است.'})

        from financial.models import Gateway
        gateway = Gateway.get_active_deposit(user, amount=amount)

        if amount < gateway.min_deposit_amount:
            raise ValidationError('حداقل میزان واریز {} تومان است.'.format(humanize_number(gateway.min_deposit_amount)))

        if amount > gateway.max_deposit_amount:
            raise ValidationError('حداکثر میزان واریز {} تومان است.'.format(humanize_number(gateway.max_deposit_amount)))

        login_activity = LoginActivity.from_request(self.context['request'])

        try:
            return gateway.create_payment_request(bank_card=bank_card, amount=amount, source=source, login_activity=login_activity)
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

    amount = serializers.SerializerMethodField()
    bank_card = serializers.SerializerMethodField()
    payment_id = serializers.SerializerMethodField()

    def get_amount(self, payment: Payment):
        return payment.amount

    def get_bank_card(self, payment: Payment):
        bank_card = payment.payment_request and payment.payment_request.bank_card

        if bank_card:
            return BankCardSerializer(bank_card).data

    def get_payment_id(self, payment: Payment):
        payment_id_request = payment.payment_id_request

        if payment_id_request:
            bank = get_bank_from_iban(payment_id_request.source_iban)

            return {
                'info': bank and bank.as_dict(),
                'iban': payment_id_request.source_iban,
            }

    class Meta:
        model = Payment
        fields = ('id', 'created', 'status', 'ref_id', 'amount', 'bank_card', 'payment_id')


class PaymentHistoryView(ListAPIView):
    serializer_class = PaymentHistorySerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'status', 'payment_request_id']

    def get_queryset(self):
        user = self.request.user

        return Payment.objects.filter(
            Q(payment_request__bank_card__user=user) |
            Q(payment_id_request__payment_id__user=user)
        ).order_by('-created')
