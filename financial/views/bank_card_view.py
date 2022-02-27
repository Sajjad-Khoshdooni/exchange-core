from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from financial.models.bank_card import BankCardSerializer, BankCard


class BankCardView(ModelViewSet):
    serializer_class = BankCardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['verified']

    def get_queryset(self):
        return BankCard.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, bank_card: BankCard):
        if bank_card.verified is None:
            raise ValidationError('شماره کارت در حال اعتبارسنجی است.')

        if bank_card.verified and BankCard.objects.filter(user=bank_card.user, verified=True).count() == 1:
            raise ValidationError('تنها شماره کارت تایید شده‌تان را نمی‌توانید حذف کنید.')

        return super().perform_destroy(bank_card)
