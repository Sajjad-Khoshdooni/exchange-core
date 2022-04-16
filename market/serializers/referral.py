import logging

from rest_framework import serializers

from accounts.models import Referral

logger = logging.getLogger(__name__)


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = ('id', 'created', 'code', 'owner_share_percent',)


class ReferralTrxSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=0)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

