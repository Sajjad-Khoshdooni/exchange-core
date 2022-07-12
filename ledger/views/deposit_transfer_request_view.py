from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer
from ledger.models import Network, Asset, DepositAddress
from accounts.models import Account
from ledger.utils.wallet_pipeline import WalletPipeline


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

    def save(self, user, **kwargs):
        network = self.validated_data('network')
        receiver_address = self.validated_data('receiver_address')

        deposit_address = DepositAddress.objects.get(
            address=receiver_address,
            netwrok=network
        )
        asset = Asset.objects.get(symbol=self.validated_data('coin'))
        wallet = asset.get_wallet(deposit_address.address_key.account)

        status = self.validated_data('status')

        transfer = Transfer.objects.update_or_create(
            network=network,
            trx_hash=self.validated_data('trx_hash'),
            defaults={
                'status': status,
                'deposit_address': deposit_address,
                'amount': self.validated_data('amount'),
                'block_hash': self.validated_data('block_hash'),
                'block_number': self.validated_data('block_number'),
                'out_address': receiver_address,
                'wallet': wallet,
                'deposit': self.validated_data('type')
            })

        if status == 'done':
            with WalletPipeline() as pipeline:
                transfer.build_trx(pipeline)
                transfer.save()

            transfer.alert_user()
        return transfer


class DepositTransferUpdateView(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    serializer_class = DepositSerializer

    def get_object(self):
        return self.request.user


