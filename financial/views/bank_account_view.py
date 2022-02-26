from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView

from financial.models.bank_card import BankAccountSerializer, BankAccount


class BankAccountView(ListAPIView):
    serializer_class = BankAccountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['verified']

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)
