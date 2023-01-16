from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from financial.models import Gateway


class GatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gateway
        fields = ('id', 'min_deposit_amount', 'max_deposit_amount')


class GatewayInfoView(RetrieveAPIView):
    serializer_class = GatewaySerializer

    def get_object(self):
        user = self.request.user
        return Gateway.get_active(user)
