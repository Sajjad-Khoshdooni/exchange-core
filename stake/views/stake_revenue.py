from rest_framework import serializers

from rest_framework.generics import ListAPIView
from stake.models import StakeRevenue


class StakeRevenueSerializer(serializers.ModelSerializer):

    class Meta:
        model = StakeRevenue
        fields = ('created', 'stake_request', 'revenue')


class StakeRevenueAPIView(ListAPIView):
    serializer_class = StakeRevenueSerializer

    def get_queryset(self):
        return StakeRevenue.objects.filter(stake_request__account=self.request.user.account)
