from django.db.models import Sum
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from accounts.models import SystemConfig
from accounts.models.user_feature_perm import UserFeaturePerm
from financial.models import Gateway, Payment
from financial.utils.ach import next_ach_clear_time
from financial.utils.user import get_today_fiat_deposits
from ledger.utils.fields import DONE
from ledger.utils.precision import get_presentation_amount


class GatewaySerializer(serializers.ModelSerializer):
    next_ach_time = serializers.SerializerMethodField()
    pay_id_enable = serializers.SerializerMethodField()
    max_deposit_amount = serializers.SerializerMethodField()
    ipg_fee_percent = serializers.SerializerMethodField()
    ipg_withdraw_fee_min = serializers.SerializerMethodField()
    ipg_withdraw_fee_max = serializers.SerializerMethodField()
    ipg_withdraw_fee_percent = serializers.SerializerMethodField()

    def get_ipg_withdraw_fee_min(self, gateway):
        system_config = SystemConfig.get_system_config()
        return system_config.ipg_withdraw_fee_min

    def get_ipg_withdraw_fee_max(self, gateway):
        system_config = SystemConfig.get_system_config()
        return system_config.ipg_withdraw_fee_max

    def get_ipg_withdraw_fee_percent(self, gateway):
        system_config = SystemConfig.get_system_config()
        return system_config.ipg_withdraw_fee_percent

    def get_next_ach_time(self, gateway):
        return next_ach_clear_time()

    def get_pay_id_enable(self, gateway):
        user = self.context['request'].user

        gateway = Gateway.get_active_pay_id_deposit()
        return bool(gateway) and user.has_feature_perm(UserFeaturePerm.PAY_ID)

    def get_ipg_fee_percent(self, gateway: Gateway):
        return get_presentation_amount(gateway.ipg_fee_percent)

    def get_max_deposit_amount(self, gateway):
        user = self.context['request'].user

        today_deposits = get_today_fiat_deposits(user)
        deposit_quota = user.get_feature_limit(UserFeaturePerm.FIAT_DEPOSIT_DAILY_LIMIT) - today_deposits

        return max(0, min(deposit_quota, gateway.max_deposit_amount))

    class Meta:
        model = Gateway
        fields = (
            'id', 'min_deposit_amount', 'max_deposit_amount', 'next_ach_time', 'pay_id_enable', 'ipg_fee_min',
            'ipg_fee_max', 'ipg_fee_percent'
        )


class GatewayInfoView(RetrieveAPIView):
    serializer_class = GatewaySerializer

    def get_object(self):
        user = self.request.user

        total = Payment.objects.filter(
            user=user,
            status=DONE
        ).aggregate(amount=Sum('amount'))['amount'] or 0

        if total < 10_000_000:
            return Gateway.get_active_deposit(user)
        else:
            return Gateway.objects.filter(active=True).order_by('-max_deposit_amount').first()
