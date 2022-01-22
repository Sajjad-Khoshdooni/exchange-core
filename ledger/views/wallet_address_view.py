from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response

from ledger.models import NetworkWallet, Asset, Network
from ledger.models.network_wallet import NetworkWalletSerializer
from ledger.utils.wallet import generate_deposit_address


class InputAddressSerializer(serializers.Serializer):
    coin = serializers.CharField()
    network = serializers.CharField()


class WalletAddressView(RetrieveAPIView):

    def retrieve(self, request, *args, **kwargs):
        serializer = InputAddressSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        asset = get_object_or_404(Asset, symbol=data['coin'])
        wallet = asset.get_wallet(request.user.account)

        network = get_object_or_404(Network, symbol=data['network'])

        # if not network.can_withdraw:
        #     raise ValidationError({'network': 'withdraw is not supported'})

        network_wallet = NetworkWallet.objects.filter(network=network, wallet=wallet).first()

        if not network_wallet:
            network_wallet = generate_deposit_address(wallet, network)

        serializer = NetworkWalletSerializer(instance=network_wallet)
        return Response(data=serializer.data)
