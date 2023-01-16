from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response

from accounts.models import User
from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from ledger.models import Network


class InputAddressSerializer(serializers.Serializer):
    coin = serializers.CharField()
    network = serializers.CharField()


class DepositAddressView(RetrieveAPIView):
    serializer_class = InputAddressSerializer
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    def retrieve(self, request, *args, **kwargs):
        if request.user.level < User.LEVEL2:
            raise ValidationError({'user': 'برای واریز ابتدا احراز هویت خود را تکمیل نمایید.'})

        serializer = InputAddressSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        network = get_object_or_404(Network, symbol=data['network'], can_deposit=True)

        deposit_address = network.get_deposit_address(request.user.account)

        return Response(data={
            'address': deposit_address.address
        })
