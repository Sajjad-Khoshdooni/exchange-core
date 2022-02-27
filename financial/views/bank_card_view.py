from django_filters.rest_framework import DjangoFilterBackend
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
