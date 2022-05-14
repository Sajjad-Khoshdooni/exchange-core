from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.views.authentication import CustomTokenAuthentication
from ledger.models import Transfer
from ledger.views.wallet_view import TransferSerializer


class WithdrawHistoryView(ListAPIView):

    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    serializer_class = TransferSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        query_params = self.request.query_params

        queryset = Transfer.objects.filter(
            wallet__account=self.request.user.account,
            deposit=False,
            hidden=False,
        ).order_by('-created')

        if 'coin' in query_params:
            queryset = queryset.filter(wallet__asset__symbol=query_params['coin'])

        return queryset


class DepositHistoryView(WithdrawHistoryView):
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    def get_queryset(self):
        query_params = self.request.query_params

        queryset = Transfer.objects.filter(
            wallet__account=self.request.user.account,
            deposit=True,
            hidden=False,
            status=Transfer.DONE
        ).order_by('-created')

        if 'coin' in query_params:
            queryset = queryset.filter(wallet__asset__symbol=query_params['coin'])

        return queryset
