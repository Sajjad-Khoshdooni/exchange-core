from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet

from financial.models.bank_card import BankAccountSerializer, BankAccount


class BankAccountView(ModelViewSet):
    serializer_class = BankAccountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['verified']

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user, deleted=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, bank_account: BankAccount):
        if bank_account.verified is None:
            raise ValidationError('شماره شبا در حال اعتبارسنجی است.')

        if bank_account.verified and BankAccount.objects.filter(user=bank_account.user, verified=True).count() == 1:
            raise ValidationError('شما باید حداقل یک شماره شبا تایید شده داشته باشید.')

        bank_account.deleted = True
        bank_account.save()
