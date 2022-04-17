import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.models import Referral

logger = logging.getLogger(__name__)


class ReferralSerializer(serializers.ModelSerializer):
    is_editable = serializers.SerializerMethodField()

    def get_is_editable(self, referral: Referral):
        return referral.owner == self.context['account']

    def to_internal_value(self, data):
        try:
            owner_share_percent = int(data['owner_share_percent'])
        except ValueError:
            raise ValidationError({'owner_share_percent': _('A valid integer is required.')})
        return super(ReferralSerializer, self).to_internal_value(
            {'owner_share_percent': owner_share_percent, 'owner': self.context['account'].id}
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
