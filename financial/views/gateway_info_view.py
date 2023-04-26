from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from financial.models import Gateway
from financial.utils.ach import next_ach_clear_time


class GatewaySerializer(serializers.ModelSerializer):
    next_ach_time = serializers.SerializerMethodField

    def get_next_ach_time(self):
        return next_ach_clear_time()

    class Meta:
        model = Gateway
        fields = ('id', 'min_deposit_amount', 'max_deposit_amount', 'next_ach_time')


class GatewayInfoView(RetrieveAPIView):
    serializer_class = GatewaySerializer

    def get_object(self):
        user = self.request.user
        return Gateway.get_active_deposit(user)
