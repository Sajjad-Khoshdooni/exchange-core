import logging
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView

from accounts.views.authentication import CustomTokenAuthentication
from ledger.models.transfer import Transfer
from ledger.utils.wallet_pipeline import WalletPipeline


logger = logging.getLogger(__name__)


class WithdrawSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField(write_only=True)
    status = serializers.CharField(max_length=8, write_only=True)

    def create(self, validated_data):
        requester_id = validated_data.get('requester_id')
        status = validated_data.get('status')
        transfer = get_object_or_404(Transfer, id=requester_id)

        valid_transitions = [
            (Transfer.PROCESSING, Transfer.PENDING),
            (Transfer.PENDING, Transfer.DONE),
            (Transfer.PENDING, Transfer.CANCELED),
            (Transfer.PROCESSING, Transfer.DONE),
            (Transfer.PROCESSING, Transfer.CANCELED),
        ]

        if transfer.source == Transfer.BINANCE:
            logger.warning('Update Binance Withdraw')

        if transfer.status == status:
            return transfer

        if (transfer.status, status) not in valid_transitions:
            raise ValidationError({'status': 'invalid status transition (%s -> %s)' % (transfer.status, status)})

        with WalletPipeline() as pipeline:
            transfer.status = status
            transfer.save(update_fields=['status'])

            if status == Transfer.DONE:
                transfer.build_trx(pipeline)

            if status in (Transfer.CANCELED, Transfer.DONE):
                pipeline.release_lock(transfer.group_id)

            transfer.alert_user()

        return transfer


class WithdrawTransferUpdateView(CreateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    serializer_class = WithdrawSerializer
