from rest_framework import serializers

from ledger.utils.precision import get_presentation_amount
from stake.models import StakeOption
from rest_framework.generics import ListAPIView


class StakeOptionSerializer(serializers.ModelSerializer):
    asset = serializers.CharField()
    apr = serializers.SerializerMethodField()
    max_amount = serializers.SerializerMethodField()
    min_amount = serializers.SerializerMethodField()

    def get_apr(self, stake_option: StakeOption):
        return get_presentation_amount(stake_option.apr)

    def get_max_amount(self, stake_option: StakeOption):
        return get_presentation_amount(stake_option.max_amount)

    def get_min_amount(self, stake_option: StakeOption):
        return get_presentation_amount(stake_option.min_amount)

    class Meta:
        model = StakeOption
        fields = ('asset', 'apr', 'enable', 'max_amount', 'min_amount', 'id')


class StakeOptionAPIView(ListAPIView):
    authentication_classes = []
    permission_classes = []

    serializer_class = StakeOptionSerializer
    queryset = StakeOption.objects.filter(enable=True)
