from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from ledger.models import Prize
from ledger.models.asset import AssetSerializerMini
from ledger.utils.wallet_pipeline import WalletPipeline


class PrizeSerializer(serializers.ModelSerializer):
    asset = AssetSerializerMini(read_only=True)
    reason = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    def update(self, prize: Prize, validated_data):
        redeemed = validated_data['redeemed']

        if redeemed is True and not prize.redeemed:
            with WalletPipeline() as pipeline:
                prize.build_trx(pipeline)

        return prize

    class Meta:
        model = Prize
        fields = ('id', 'amount', 'scope', 'asset', 'redeemed', 'reason', 'created')
        read_only_fields = ('id', 'amount', 'scope', 'coin', 'created')

    def get_reason(self, prize: Prize):
        return ''

    def get_amount(self, prize: Prize):
        return prize.asset.get_presentation_amount(prize.amount)


class PrizeView(ModelViewSet):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    serializer_class = PrizeSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return Prize.objects.filter(account=self.request.user.account, amount__gt=0)
