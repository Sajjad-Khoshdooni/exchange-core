from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response

from ledger.models import NetworkAddress, Asset, Network
from ledger.models.network_address import NetworkAddressSerializer


class InputAddressSerializer(serializers.Serializer):
    coin = serializers.CharField()
    network = serializers.CharField()


class DepositAddressView(RetrieveAPIView):

    def retrieve(self, request, *args, **kwargs):
        serializer = InputAddressSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        network = get_object_or_404(Network, symbol=data['network'])

        network_address = NetworkAddress.objects.get_or_create(account=request.user.account, network=network)

        serializer = NetworkAddressSerializer(instance=network_address)
        return Response(data=serializer.data)
