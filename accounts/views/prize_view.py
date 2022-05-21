from django.db import transaction
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.viewsets import ModelViewSet

from ledger.models import Prize


class PrizeSerializer(serializers.ModelSerializer):

    coin = serializers.SerializerMethodField()

    def update(self, prize: Prize, validated_data):
        redeemed = validated_data['redeemed']

        if redeemed is True and not prize.redeemed:
            with transaction.atomic():
                prize.build_trx()

        return prize

    class Meta:
        model = Prize
        fields = ('id', 'amount', 'scope', 'coin', 'redeemed')
        read_only_fields = ('id', 'amount', 'scope', 'coin')

    def get_coin(self, prize: Prize):
        return prize.asset.symbol


class PrizeView(ModelViewSet):
    authentication_classes = (SessionAuthentication, )
    serializer_class = PrizeSerializer

    def get_queryset(self):
        return Prize.objects.filter(account=self.request.user.account)
