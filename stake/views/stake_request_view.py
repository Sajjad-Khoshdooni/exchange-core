from rest_framework import serializers

from stake.models import StakeRequest


class StakeRequestSerializer(serializers.ModelSerializer):

    stake_option = serializers.
    class Meta:
        model = StakeRequest
        fields =