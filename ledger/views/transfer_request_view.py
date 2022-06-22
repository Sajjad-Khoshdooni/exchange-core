from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from ledger.models.transfer import Transfer
from ledger.models import Network, DepositAddress, Asset
from accounts.models import Account


class TransferViewSerializer(serializers.ModelSerializer):
    network_symbol = serializers.CharField(max_length=4)
    sender_address = serializers.CharField(max_length=256)
    receiver_address = serializers.CharField(max_length=256)
    type = serializers.CharField(max_length=8)
    coin = serializers.CharField(max_length=8)

    class Meta:
        model = Transfer
        fields = ['status', 'amount', 'trx_hash', 'block_hash', 'type',
                  'block_number', 'network_symbol', 'sender_address', 'receiver_address', 'coin']


class TransferUpdateView(APIView):
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        global out_address, deposit_address
        serializer = TransferViewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        acc = Account.objects.get(user=request.user)
        network = Network.objects.get(symbol=data['network_symbol'])
        deposit_address = DepositAddress().new_deposit_address(account=acc, network=network)
        asset = Asset.objects.get(symbol=data['coin'])
        wallet = asset.get_wallet(acc)

        Transfer.objects.update_or_create(deposit_address=deposit_address,
                                            network=network, amount=data['amount'],
                                            trx_hash=data['trx_hash'], block_hash=data['block_hash'],
                                            block_number=data['block_number'], out_address=data['receiver_address'],
                                            wallet=wallet,
                                          defaults={
                                              'status': data['status'],
                                              'deposit': data['type'],
                                          })
        return Response(201)
