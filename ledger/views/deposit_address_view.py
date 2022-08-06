from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from ledger.models import Network
from ledger.utils.encoding import base58_from_hex


class InputAddressSerializer(serializers.Serializer):
    coin = serializers.CharField()
    network = serializers.CharField()


class DepositAddressView(RetrieveAPIView):
    serializer_class = InputAddressSerializer
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    def retrieve(self, request, *args, **kwargs):
        serializer = InputAddressSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        network = get_object_or_404(Network, symbol=data['network'])

        deposit_address = network.get_deposit_address(request.user.account)

        return Response(data={
            'address': deposit_address.address
        })
