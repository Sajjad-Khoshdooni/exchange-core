from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from ledger.models import Prize
from ledger.utils.wallet_pipeline import WalletPipeline


class PrizeSerializer(serializers.ModelSerializer):
    coin = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()

    def update(self, prize: Prize, validated_data):
        redeemed = validated_data['redeemed']

        if redeemed is True and not prize.redeemed:
            with WalletPipeline() as pipeline:
                prize.build_trx(pipeline)

        return prize

    class Meta:
        model = Prize
        fields = ('id', 'amount', 'scope', 'coin', 'redeemed')
        read_only_fields = ('id', 'amount', 'scope', 'coin')

    def get_coin(self, prize: Prize):
        return prize.asset.symbol

    def get_reason(self, prize: Prize):
        return Prize.VERBOSE.get(prize.scope, '')


class PrizeView(ModelViewSet):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    serializer_class = PrizeSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return Prize.objects.filter(account=self.request.user.account)
