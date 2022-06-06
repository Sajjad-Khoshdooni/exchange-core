from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer


class TransferViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ['status', 'deposit_address', 'network_symbol', 'amount', 'deposit', 'trx_hash', 'block_hash',
                  'block_number', 'out_address']


class TransferUpdateView(APIView):
    def post(self, request):
        serializer = TransferViewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        Transfer.objects.update_or_create(status=data['status'], deposit_address=data['deposit_address'],
                                            network__symbol=data['network_symbol'],
                                            amount=data['amount'], deposit=data['deposit'],
                                            trx_hash=data['trx_hash'], block_hash=data['block_hash'],
                                            block_number=data['block_number'], out_address=data['out_address'])
        return Response(201)
