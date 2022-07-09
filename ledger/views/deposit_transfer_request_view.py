from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer
from ledger.models import Network, DepositAddress, Asset
from accounts.models import Account


class DepositSerializer(serializers.ModelSerializer):
    network = serializers.CharField(max_length=4)
    sender_address = serializers.CharField(max_length=256)
    receiver_address = serializers.CharField(max_length=256)
    type = serializers.CharField(max_length=8)
    coin = serializers.CharField(max_length=8)

    class Meta:
        model = Transfer
        fields = ['status', 'amount', 'trx_hash', 'block_hash', 'type',
                  'block_number', 'network', 'sender_address', 'receiver_address', 'coin']

    def save(self, **kwargs):
        account = Account.objects.get(user=self.context['request']['user'])
        network = Network.objects.get(symbol=self.validated_data('network'))
        deposit_address = network.get_deposit_address(account)
        asset = Asset.objects.get(symbol=self.validated_data('coin'))
        wallet = asset.get_wallet(account)

        Transfer.objects.update_or_create(
            network=network,
            trx_hash=self.validated_data('trx_hash'),
            defaults={
                'status': self.validated_data('status'),
                'deposit_address': deposit_address,
                'amount': self.validated_data('amount'),
                'block_hash': self.validated_data('block_hash'),
                'block_number': self.validated_data('block_number'),
                'out_address': self.validated_data('receiver_address'),
                'wallet': wallet,
                'deposit': self.validated_data('type')
            })


class DepositTransferUpdateView(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    serializer_class = DepositSerializer


