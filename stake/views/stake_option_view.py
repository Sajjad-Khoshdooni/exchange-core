from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models.asset import AssetSerializerMini
from ledger.utils.precision import get_presentation_amount
from stake.models import StakeOption, StakeRequest


class StakeOptionSerializer(serializers.ModelSerializer):
    asset = AssetSerializerMini(read_only=True)
    apr = serializers.SerializerMethodField()
    fee = serializers.SerializerMethodField()
    user_max_amount = serializers.SerializerMethodField()
    user_min_amount = serializers.SerializerMethodField()

    user_available_amount = serializers.SerializerMethodField()

    total_cap = serializers.SerializerMethodField()

    filled_cap_percent = serializers.SerializerMethodField()
    enable = serializers.SerializerMethodField()

    def get_total_cap(self, stake_option: StakeOption):
        return get_presentation_amount(stake_option.total_cap)

    def get_filled_cap_percent(self, stake_option: StakeOption):
        return self.context['caps'].get(stake_option.id, 0) / stake_option.total_cap * 100

    def get_apr(self, stake_option: StakeOption):
        return get_presentation_amount(stake_option.apr)

    def get_fee(self, stake_option: StakeOption):
        return get_presentation_amount(stake_option.fee)

    def is_staking_available(self, stake_option: StakeOption):
        return self.context['caps'].get(stake_option.id, 0) >= stake_option.user_min_amount

    def get_user_max_amount(self, stake_option: StakeOption):
        if not self.is_staking_available(stake_option):
            return '-'
        return get_presentation_amount(stake_option.user_max_amount)

    def get_user_min_amount(self, stake_option: StakeOption):
        if not self.is_staking_available(stake_option):
            return '-'

        return get_presentation_amount(stake_option.user_min_amount)

    def get_user_available_amount(self, stake_option: StakeOption):
        user = self.context.get('user')

        if user:
            return stake_option.get_free_amount_per_user(user=user)
        else:
            return stake_option.user_max_amount

    def get_enable(self, stake_option: StakeOption):
        return self.is_staking_available(stake_option)

    class Meta:
        model = StakeOption
        fields = ('id', 'asset', 'apr', 'enable', 'user_max_amount', 'user_min_amount', 'user_available_amount',
                  'total_cap', 'filled_cap_percent', 'landing', 'precision', 'fee')


class StakeOptionAPIView(ListAPIView):
    permission_classes = []

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['landing']

    serializer_class = StakeOptionSerializer
    queryset = StakeOption.objects.filter(enable=True).order_by('-apr')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            ctx['user'] = self.request.user

        ctx['caps'] = dict(StakeRequest.objects.filter(
            stake_option__enable=True,
            status__in=(StakeRequest.PROCESS, StakeRequest.PENDING, StakeRequest.DONE),
        ).values('stake_option').annotate(sum=Sum('amount')).values_list('stake_option', 'sum'))

        return ctx
