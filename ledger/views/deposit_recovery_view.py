from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ModelSerializer

from ledger.models.asset import CoinField
from ledger.models.network import NetworkField
from ledger.models import DepositRecoveryRequest


class DepositRecoverySerializer(ModelSerializer):
    coin = CoinField(required=True)
    network = NetworkField(required=True)

    class Meta:
        model = DepositRecoveryRequest
        fields = ('coin', 'network', 'memo', 'amount', 'trx_hash', 'receiver_address',)
        extra_kwargs = {
            'memo': {'required': False},
            'description': {'required': False}
        }


class DepositRecoveryView(CreateAPIView):
    serializer_class = DepositRecoverySerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
