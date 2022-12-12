from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.authentication import CustomTokenAuthentication
from ledger.models import Transfer
from ledger.models.asset import AssetSerializerMini


class TransferSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()
    asset = AssetSerializerMini(source='wallet.asset', read_only=True)
    is_internal = serializers.SerializerMethodField()

    def get_link(self, transfer: Transfer):
        return transfer.get_explorer_link()

    def get_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.total_amount - transfer.fee_amount)

    def get_fee_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.fee_amount)

    def get_network(self, transfer: Transfer):
        return transfer.network.symbol

    def get_is_internal(self, transfer: Transfer):
        return transfer.source == Transfer.INTERNAL

    class Meta:
        model = Transfer
        fields = ('created', 'amount', 'status', 'link', 'out_address', 'asset', 'network', 'trx_hash',
                  'fee_amount', 'is_internal')


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
        ).order_by('-created')

        if 'coin' in query_params:
            queryset = queryset.filter(wallet__asset__symbol=query_params['coin'])

        return queryset
