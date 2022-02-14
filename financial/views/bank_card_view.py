from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView

from financial.models.bank_card import BankCardSerializer, BankCard


class BankCardView(ListAPIView):
    serializer_class = BankCardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['verified']

    def get_queryset(self):
        return BankCard.objects.filter(user=self.request.user)
