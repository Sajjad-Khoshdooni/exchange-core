from django.db.models import Q
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models import NetworkAsset
from ledger.utils.precision import get_presentation_amount


class NetworkAssetSerializer(serializers.ModelSerializer):
    network = serializers.SerializerMethodField()
    coin = serializers.SerializerMethodField()
    network_name = serializers.SerializerMethodField()

    withdraw_fee = serializers.SerializerMethodField()
    withdraw_min = serializers.SerializerMethodField()

    def get_coin(self, network_asset: NetworkAsset):
        return network_asset.asset.symbol

    def get_network(self, network_asset: NetworkAsset):
        return network_asset.network.symbol

    def get_network_name(self, network_asset: NetworkAsset):
        return network_asset.network.name

    def get_withdraw_min(self, network_asset: NetworkAsset):
        return get_presentation_amount(network_asset.withdraw_min)

    def get_withdraw_fee(self, network_asset: NetworkAsset):
        return get_presentation_amount(network_asset.withdraw_fee)

    class Meta:
        fields = ('coin', 'network', 'network_name', 'withdraw_fee', 'withdraw_min')
        model = NetworkAsset


class NetworkAssetView(ListAPIView):
    authentication_classes = []
    permission_classes = []

    serializer_class = NetworkAssetSerializer

    queryset = NetworkAsset.objects.filter(
        Q(network__can_deposit=True) | Q(network__can_withdraw=True),
        asset__enable=True,
    ).distinct()
