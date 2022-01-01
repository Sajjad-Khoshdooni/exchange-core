import decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response

from ledger.models import NetworkWallet, Asset, Network, NetworkAsset, Wallet
from ledger.models.network_wallet import NetworkWalletSerializer
from ledger.utils.price import get_all_assets_prices, get_tether_irt_price
from ledger.utils.wallet import generate_deposit_address


class InputAddressSerializer(serializers.Serializer):
    wallet_id = serializers.IntegerField()
    network_id = serializers.CharField()


class WalletAddressView(RetrieveAPIView):

    def retrieve(self, request, *args, **kwargs):
        serializer = InputAddressSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        wallet = get_object_or_404(Wallet, id=data['wallet_id'])

        if wallet.account.user != request.user:
            raise PermissionDenied

        network = get_object_or_404(Network, id=data['network_id'])

        if not network.can_withdraw:
            raise ValidationError({'network': 'withdraw is not supported'})

        network_wallet = NetworkWallet.objects.filter(network=network, wallet=wallet).first()

        if not network_wallet:
            network_wallet = generate_deposit_address(wallet, network)

        serializer = NetworkWalletSerializer(instance=network_wallet)
        return Response(data=serializer.data)

