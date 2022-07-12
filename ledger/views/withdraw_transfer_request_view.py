from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import get_object_or_404, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer
from ledger.utils.wallet_pipeline import WalletPipeline


class WithdrawSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField()
    status = serializers.CharField(max_length=8)

    def update(self, **kwargs):
        requester_id = self.validated_data.get('requester_id')
        status = self.validated_data.get('status')

        transfer = get_object_or_404(Transfer, id=requester_id)
        transfer.status = status
        transfer.save()

        if status == 'done':
            with WalletPipeline() as pipeline:
                transfer.build_trx(pipeline)
                pipeline.release_lock(transfer.group_id)
            transfer.alert_user()

        return transfer


class WithdrawTransferUpdateView(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    serializer_class = WithdrawSerializer

    def get_object(self):
        return self.request.user
