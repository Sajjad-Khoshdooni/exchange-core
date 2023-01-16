from django.db.models import Max, Min
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models.asset import Asset
from ledger.utils.price import get_trading_price_irt, BUY, SELL
from market.models import Order


class AssetListSerializer(serializers.ModelSerializer):
    ask = serializers.SerializerMethodField()
    bid = serializers.SerializerMethodField()

    def get_ask(self, asset: Asset):
        asks = self.context['asks']
        price = asks.get(asset.symbol)

        if not price:
            price = get_trading_price_irt(asset.symbol, SELL)

        return asset.get_presentation_price_irt(price)

    def get_bid(self, asset: Asset):
        bids = self.context['bids']
        price = bids.get(asset.symbol)

        if not price:
            price = get_trading_price_irt(asset.symbol, BUY)

        return asset.get_presentation_price_irt(price)

    class Meta:
        model = Asset
        fields = ('symbol', 'ask', 'bid')
        ref_name = 'market asset'


class MarketInfoView(ListAPIView):
    queryset = Asset.live_objects.filter(trade_enable=True).exclude(symbol=Asset.IRT)
    serializer_class = AssetListSerializer
    authentication_classes = []
    permission_classes = []

    def get_serializer_context(self):
        ctx = super(MarketInfoView, self).get_serializer_context()

        bids = dict(Order.open_objects.filter(
            side=BUY,
            symbol__base_asset__symbol=Asset.IRT,
            symbol__enable=True,
        ).values('symbol__asset__symbol').annotate(price=Max('price')).values_list('symbol__asset__symbol', 'price'))

        asks = dict(Order.open_objects.filter(
            side=SELL,
            symbol__base_asset__symbol=Asset.IRT,
            symbol__enable=True,
        ).values('symbol__asset__symbol').annotate(price=Min('price')).values_list('symbol__asset__symbol', 'price'))

        return {
            **ctx,
            'asks': asks,
            'bids': bids
        }
