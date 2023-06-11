from django.db.models import Sum
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from financial.models import Gateway, Payment
from financial.utils.ach import next_ach_clear_time
from ledger.utils.fields import DONE


class GatewaySerializer(serializers.ModelSerializer):
    next_ach_time = serializers.SerializerMethodField()

    def get_next_ach_time(self, gateway):
        return next_ach_clear_time()

    class Meta:
        model = Gateway
        fields = ('id', 'min_deposit_amount', 'max_deposit_amount', 'next_ach_time')


class GatewayInfoView(RetrieveAPIView):
    serializer_class = GatewaySerializer

    def get_object(self):
        user = self.request.user

        total = Payment.objects.filter(
            payment_request__bank_card__user=user,
            status=DONE
        ).aggregate(amount=Sum('payment_request__amount'))['amount'] or 0

        if total < 10_000_000:
            return Gateway.get_active_deposit(user)
        else:
            return Gateway.objects.filter(active=True).order_by('-max_deposit_amount').first()
