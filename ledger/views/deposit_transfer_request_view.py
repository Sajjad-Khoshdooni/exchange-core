from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView

from accounts.views.authentication import CustomTokenAuthentication
from ledger.models import Network, Asset, DepositAddress
from ledger.models.transfer import Transfer
from ledger.utils.wallet_pipeline import WalletPipeline


class DepositSerializer(serializers.ModelSerializer):
    network = serializers.CharField(max_length=4, write_only=True)
    sender_address = serializers.CharField(max_length=256, write_only=True)
    receiver_address = serializers.CharField(max_length=256, write_only=True)
    coin = serializers.CharField(max_length=8, write_only=True)

    class Meta:
        model = Transfer
        fields = ['status', 'amount', 'trx_hash', 'block_hash',
                  'block_number', 'network', 'sender_address', 'receiver_address', 'coin']

    def create(self, validated_data):
        network_symbol = validated_data.get('network')
        sender_address = validated_data.get('sender_address')
        receiver_address = validated_data.get('receiver_address')
        network = Network.objects.get(symbol=network_symbol)

        deposit_address = DepositAddress.objects.get(
            address=receiver_address,
            network=network
        )
        asset = Asset.objects.get(symbol=validated_data.get('coin'))
        wallet = asset.get_wallet(deposit_address.address_key.account)

        status = validated_data.get('status')

        if status not in (Transfer.PENDING, Transfer.DONE, Transfer.CANCELED):
            raise ValidationError({'status': 'invalid status %s' % status})

        prev_transfer = Transfer.objects.filter(
            network=network,
            trx_hash=validated_data.get('trx_hash'),
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
            with WalletPipeline() as pipeline:
                transfer = Transfer.objects.create(
                    network=network,
                    trx_hash=validated_data.get('trx_hash'),
                    deposit=True,
                    status=status,
                    deposit_address=deposit_address,
                    amount=validated_data.get('amount'),
                    block_hash=validated_data.get('block_hash'),
                    block_number=validated_data.get('block_number'),
                    out_address=sender_address,
                    wallet=wallet
                )

                if status == Transfer.DONE:
                    transfer.build_trx(pipeline)

                transfer.alert_user()

            return transfer


class DepositTransferUpdateView(CreateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    serializer_class = DepositSerializer
