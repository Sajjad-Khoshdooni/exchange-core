from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet

from financial.models.bank_card import BankAccountSerializer, BankAccount


class BankAccountView(ModelViewSet):
    serializer_class = BankAccountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['verified']

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
