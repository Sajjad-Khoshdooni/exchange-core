from rest_framework import serializers

from rest_framework.generics import ListAPIView
from stake.models import StakeRevenue
from stake.views.stake_request_view import StakeRequestSerializer


class StakeRevenueSerializer(serializers.ModelSerializer):
    stake_request = StakeRequestSerializer()

    class Meta:
        model = StakeRevenue
        fields = ('created', 'stake_request', 'revenue')


class StakeRevenueAPIView(ListAPIView):
    serializer_class = StakeRevenueSerializer

    def get_queryset(self):
        return StakeRevenue.objects.filter(stake_request__account=self.request.user.account)
