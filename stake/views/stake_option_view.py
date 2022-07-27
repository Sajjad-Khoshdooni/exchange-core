from rest_framework import serializers

from stake.models import StakeOption
from rest_framework.generics import ListAPIView


class StakeOptionSerializer(serializers.ModelSerializer):
    asset = serializers.CharField()

    class Meta:
        model = StakeOption
        fields = ('asset', 'apr', 'enable', 'max_amount', 'min_amount')


class StakeOptionAPIView(ListAPIView):
    serializer_class = StakeOptionSerializer
    queryset = StakeOption.objects.filter(enable=True)
