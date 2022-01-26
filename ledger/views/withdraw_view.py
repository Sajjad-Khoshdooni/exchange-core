from rest_framework import serializers
from rest_framework.generics import get_object_or_404, CreateAPIView

from ledger.models import DepositAddress, Asset, Network, Transfer


class WithdrawSerializer(serializers.ModelSerializer):
    address = serializers.CharField(write_only=True)
    coin = serializers.CharField(write_only=True)
    network = serializers.CharField(write_only=True)

    def validate(self, attrs):
        account = self.context['request'].user.account
        asset = get_object_or_404(Asset, symbol=attrs['coin'])
        network = get_object_or_404(Network, symbol=attrs['network'])

        return {
            'deposit': False,
            'network': network,
            'wallet': asset.get_wallet(account),
            'amount': attrs['amount'],
            'out_address': attrs['address']
        }

    class Meta:
        model = Transfer
        fields = ('amount', 'address', 'coin', 'network')


class WithdrawView(CreateAPIView):
    serializer_class = WithdrawSerializer
