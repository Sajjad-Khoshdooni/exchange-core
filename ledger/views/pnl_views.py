from datetime import timedelta

from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ledger.models import PNLHistory


class PNLOverview(APIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request):
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        profit_info = PNLHistory.objects.filter(
            account=self.request.user.account, date__gt=today - timedelta(days=30)
        ).aggregate(
            cumulative_profit_30=Sum('profit'),
            cumulative_profit_7=Sum('profit', filter=Q(date__gt=today - timedelta(days=7))),
            last_profit=Sum('profit', filter=Q(date__gte=today))
        )

        return Response({
            '1': profit_info['last_profit'],
            '7': profit_info['cumulative_profit_7'],
            '30': profit_info['cumulative_profit_30'],
        })
