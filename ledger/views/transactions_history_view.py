from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.views.authentication import CustomTokenAuthentication
from ledger.models import Transfer


class TransferSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()
    coin = serializers.SerializerMethodField()

    def get_link(self, transfer: Transfer):
        return transfer.get_explorer_link()

    def get_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.total_amount - transfer.fee_amount)

    def get_fee_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.fee_amount)

    def get_coin(self, transfer: Transfer):
        return transfer.wallet.asset.symbol

    def get_network(self, transfer: Transfer):
        return transfer.network.symbol

    class Meta:
        model = Transfer
        fields = ('created', 'amount', 'status', 'link', 'out_address', 'coin', 'network', 'trx_hash', 'fee_amount')



class WithdrawHistoryView(ListAPIView):

    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)

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
        ).order_by('-created')

        if 'coin' in query_params:
            queryset = queryset.filter(wallet__asset__symbol=query_params['coin'])

        return queryset
