import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView

from accounts.authentication import CustomTokenAuthentication
from ledger.models.transfer import Transfer
from ledger.utils.wallet_pipeline import WalletPipeline


logger = logging.getLogger(__name__)


class WithdrawSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField(write_only=True, source='id')
    status = serializers.CharField(max_length=8, write_only=True)
    trx_hash = serializers.CharField(max_length=128, write_only=True, allow_blank=True, allow_null=True, required=False)
    block_hash = serializers.CharField(max_length=128, write_only=True, allow_blank=True, required=False)
    block_number = serializers.IntegerField(write_only=True, allow_null=True, required=False)

    class Meta:
        model = Transfer
        fields = ['status', 'requester_id', 'trx_hash', 'block_hash', 'block_number']
        ref_name = 'Withdraw Update Serializer'

    def create(self, validated_data):
        requester_id = validated_data.get('id')
        status = validated_data.get('status')
        transfer = get_object_or_404(Transfer, id=requester_id)

        valid_transitions = [
            (Transfer.PENDING, Transfer.PENDING),
            (Transfer.PENDING, Transfer.DONE),
            (Transfer.PENDING, Transfer.CANCELED),
            (Transfer.PROCESSING, Transfer.DONE),
            (Transfer.PROCESSING, Transfer.CANCELED),
        ]

        if transfer.source != Transfer.SELF:
            logger.error('Update Binance Withdraw', extra={
                'requester_id': requester_id,
                'status': status
            })
            raise ValidationError({'requester_id': 'invalid transfer source!'})

        if transfer.status == status and status != Transfer.PENDING:
            return transfer

        if (transfer.status, status) not in valid_transitions:
            raise ValidationError({'status': 'invalid status transition (%s -> %s)' % (transfer.status, status)})

        with WalletPipeline() as pipeline:
            transfer.status = status
            transfer.trx_hash = validated_data.get('trx_hash')
            transfer.block_hash = validated_data.get('block_hash') or ''
            transfer.block_number = validated_data.get('block_number')

            if status in [Transfer.CANCELED, Transfer.DONE]:
                pipeline.release_lock(transfer.group_id)
                transfer.finished_datetime = timezone.now()

            if status == Transfer.DONE:
                transfer.build_trx(pipeline)

            transfer.save(update_fields=['status', 'trx_hash', 'block_hash', 'block_number', 'finished_datetime'])
            transfer.alert_user()

        return transfer


class WithdrawTransferUpdateView(CreateAPIView, UserPassesTestMixin):
    authentication_classes = [CustomTokenAuthentication]
    serializer_class = WithdrawSerializer

    def test_func(self):
        return self.request.user.has_perm('ledger.change_transfer')
