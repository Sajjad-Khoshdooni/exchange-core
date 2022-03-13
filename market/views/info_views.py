from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models.asset import Asset
from ledger.utils.price import get_trading_price_irt, BUY, SELL
from ledger.utils.price_manager import PriceManager


class AssetListSerializer(serializers.ModelSerializer):
    ask = serializers.SerializerMethodField()
    bid = serializers.SerializerMethodField()

    def get_ask(self, asset: Asset):
        price = get_trading_price_irt(asset.symbol, SELL)
        return asset.get_presentation_price_irt(price)

    def get_bid(self, asset: Asset):
        price = get_trading_price_irt(asset.symbol, BUY)
        return asset.get_presentation_price_irt(price)

    class Meta:
        model = Asset
        fields = ('symbol', 'ask', 'bid')


class MarketInfoView(ListAPIView):
    queryset = Asset.live_objects.all().exclude(symbol=Asset.IRT)
    serializer_class = AssetListSerializer
    authentication_classes = []
    permission_classes = []

    def list(self, request, *args, **kwargs):
        with PriceManager(fetch_all=True):
            return super(MarketInfoView, self).list(request, *args, **kwargs)
