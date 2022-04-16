from django.db.models import Q, DateField, Case, When, F, Sum
from django.db.models.functions import Cast
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from accounts.models import Referral
from market.models import ReferralTrx
from market.serializers.referral import ReferralTrxSerializer, ReferralSerializer


class ReferralListAPIView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    serializer_class = ReferralSerializer

    def get_queryset(self):
        return Referral.objects.filter(owner=self.request.user.account).union(
            Referral.objects.filter(id=self.request.user.account.referred_by_id)
        )


class ReferralReportAPIView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    serializer_class = ReferralTrxSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['referral']

    def get_queryset(self):
        qs = ReferralTrx.objects.filter(
            Q(referral__owner=self.request.user.account) | Q(trader=self.request.user.account)
        ).annotate(
            date=Cast('created', DateField()),
            received_amount=Case(
                When(trader=self.request.user.account, then=F('trader_amount')),
                When(referral__owner=self.request.user.account, then=F('referrer_amount'))
            )
        ).values('date').annotate(amount=Sum('received_amount'))
        return qs
