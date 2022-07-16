from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import UpdateAPIView

from accounts.views.authentication import CustomTokenAuthentication
from ledger.models import Network, Asset, DepositAddress
from ledger.models.transfer import Transfer
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

    def save(self, **kwargs):
        network_symbol = self.validated_data.get('network')
        sender_address = self.validated_data.get('sender_address')
        receiver_address = self.validated_data.get('receiver_address')
        network = Network.objects.get(symbol=network_symbol)

        print(receiver_address, network_symbol)

        deposit_address = DepositAddress.objects.get(
            address=receiver_address,
            network=network
        )
        asset = Asset.objects.get(symbol=self.validated_data.get('coin'))
        wallet = asset.get_wallet(deposit_address.address_key.account)

        status = self.validated_data.get('status')

        if status not in (Transfer.PENDING, Transfer.DONE, Transfer.CANCELED):
            raise ValidationError({'status': 'invalid status %s' % status})

        prev_transfer = Transfer.objects.filter(
            network=network,
            trx_hash=self.validated_data.get('trx_hash'),
            deposit=True
        ).order_by('-created').first()

        valid_transitions = [
            (Transfer.PENDING, Transfer.DONE),
            (Transfer.PENDING, Transfer.CANCELED),
        ]

        if prev_transfer:
            if prev_transfer.status == status:
                return prev_transfer

            if (prev_transfer.status, status) not in valid_transitions:
                raise ValidationError({'status': 'invalid status transition (%s -> %s)' % (prev_transfer.status, status)})

            prev_transfer.status = status
            prev_transfer.save(update_fields=['status'])

            return prev_transfer

        else:
            transfer = Transfer.objects.create(
                network=network,
                trx_hash=self.validated_data.get('trx_hash'),
                deposit=True,
                status=status,
                deposit_address=deposit_address,
                amount=self.validated_data.get('amount'),
                block_hash=self.validated_data.get('block_hash'),
                block_number=self.validated_data.get('block_number'),
                out_address=sender_address,
                wallet=wallet
            )

            if status == Transfer.DONE:
                with WalletPipeline() as pipeline:
                    transfer.build_trx(pipeline)
                    transfer.save()

                transfer.alert_user()

            return transfer


class DepositTransferUpdateView(UpdateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    serializer_class = DepositSerializer

    def get_object(self):
        return self.request.user
