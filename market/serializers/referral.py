import logging

from rest_framework import serializers

from accounts.models import Referral

logger = logging.getLogger(__name__)


class ReferralSerializer(serializers.ModelSerializer):
    is_editable = serializers.SerializerMethodField()

    def get_is_editable(self, referral: Referral):
        return referral.owner == self.context['account']

    def to_internal_value(self, data):
        return super(ReferralSerializer, self).to_internal_value(
            {'owner_share_percent': int(data['owner_share_percent']), 'owner': self.context['account'].id}
        )

    class Meta:
        model = Referral
        fields = ('id', 'owner', 'created', 'code', 'owner_share_percent', 'is_editable')
        read_only_fields = ('id', 'created', 'code', 'is_editable')
        extra_kwargs = {
            'owner': {'write_only': True},
        }


class ReferralTrxSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=0)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

