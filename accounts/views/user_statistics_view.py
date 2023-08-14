from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from accounting.models import TradeRevenue
from accounts.models import User
from financial.utils.withdraw_limit import FIAT_WITHDRAW_LIMIT, CRYPTO_WITHDRAW_LIMIT, MILLION


class TradeSerializer(serializers.Serializer):
    class Meta:
        model = TradeRevenue
        fields = ['symbol', 'side', 'amount', 'price', 'source', 'fee_revenue', 'value', 'coin_price',
                  'base_usdt_price']


class UserStatisticsSerializer(serializers.Serializer):
    all_trades = TradeSerializer(many=True, read_only=True)
    last_month_trades = TradeSerializer(many=True, read_only=True)
    fiat_withdraw_limit = serializers.IntegerField(read_only=True)
    crypto_withdraw_limit = serializers.IntegerField(read_only=True)
    fiat_deposit_limit = serializers.IntegerField(read_only=True)


class UserStatisticsView(APIView):
    def get(self, request):
        user = request.user
        all_trades = TradeRevenue.objects.filter(Q(account=user.get_account()))
        last_month_trades = TradeRevenue.objects.filter(
            Q(account=user.get_account()) & Q(created__gte=timezone.now() - timedelta(days=30)))
        fiat_withdraw_limit = FIAT_WITHDRAW_LIMIT[user.level]
        crypto_withdraw_limit = CRYPTO_WITHDRAW_LIMIT[user.level]
        fiat_deposit_limit = 50 * MILLION if user.level > User.LEVEL1 else 0
        serializer = UserStatisticsSerializer(
            {
                'all_trades': all_trades,
                'last_month_trades': last_month_trades,
                'fiat_withdraw_limit': fiat_withdraw_limit,
                'crypto_withdraw_limit': crypto_withdraw_limit,
                'fiat_deposit_limit': fiat_deposit_limit
            }
        )
        return Response(serializer.data)
