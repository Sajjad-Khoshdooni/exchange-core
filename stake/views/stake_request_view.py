from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet
from stake.models import StakeRequest


class StakeRequestSerializer(serializers.ModelSerializer):
    # stake_option =
    class Meta:
        model = StakeRequest
        fields = ('amount', 'stake_option')


class StakeRequestAPIView(ModelViewSet):
    serializer_class = StakeRequestSerializer
    queryset = StakeRequest.objects.all()

