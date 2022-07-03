from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer


class TransferViewSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField()
    status = serializers.CharField(max_length=8)


class WithdrawTransferUpdateView(APIView):
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = TransferViewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        if not Transfer.objects.filter(id=data['requester_id']).exists():
            return Response(404)

        transfer = Transfer.objects.filter(id=data['requester_id'])
        transfer.status = data['status']
        transfer.save()
        return Response(201)
