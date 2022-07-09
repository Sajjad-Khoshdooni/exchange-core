from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import get_object_or_404, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer


class WithdrawSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField()
    status = serializers.CharField(max_length=8)

    def update(self, instance, validated_data):
        requester_id = validated_data.get('requester_id')
        status = validated_data.get('status')

        transfer = get_object_or_404(Transfer, id=requester_id)
        transfer.status = status
        transfer.save()
        return


class WithdrawTransferUpdateView(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    serializer_class = WithdrawSerializer

