from datetime import datetime, timedelta

from rest_framework import serializers
from rest_framework.generics import ListAPIView

from collector.models import CoinMarketCap
from ledger.models import Asset
from ledger.models.asset import AssetSerializerMini
from ledger.utils.price import get_all_assets_prices, get_tether_irt_price, BUY


class AssetSerializerBuilder(AssetSerializerMini):
    price_usdt = serializers.SerializerMethodField()
    price_irt = serializers.SerializerMethodField()
    weekly_trend_url = serializers.SerializerMethodField()
    irt_price_changed_percent_24h = serializers.SerializerMethodField()
    is_cash = serializers.SerializerMethodField()
    change_24h = serializers.SerializerMethodField()
    change_7d = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ()

    def get_price_usdt(self, asset: Asset):
        prices = self.context['prices']
        price = prices[asset.symbol]
        return asset.get_presentation_price_usdt(price)

    def get_price_irt(self, asset: Asset):
        prices = self.context['prices']
        tether_irt = self.context['tether_irt']
        price = prices[asset.symbol] * tether_irt
        return asset.get_presentation_price_irt(price)

    def get_weekly_trend_url(self, asset: Asset):
        cap = CoinMarketCap.objects.filter(symbol=asset.symbol).first()
        if cap:
            return 'https://s3.coinmarketcap.com/generated/sparklines/web/7d/2781/%d.svg' % cap.internal_id
        else:
            return '/'

    def get_change24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.change_24h

    def get_change7d(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.change_7d

    def get_cap(self, asset) -> CoinMarketCap:
        return self.context['caps'].get(asset.symbol)

    @classmethod
    def create_serializer(cls,  prices: bool = True):
        fields = AssetSerializerMini.Meta.fields

        if prices:
            fields = (*fields, 'price_usdt', 'price_irt', 'weekly_trend_url', 'change_24h', 'change_7d')

        class Serializer(cls):
            pass

        Serializer.Meta.fields = fields

        return Serializer


class AssetsView(ListAPIView):

    authentication_classes = []
    permission_classes = []
    queryset = Asset.live_objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        if self.get_serializer_option('prices'):
            ctx['prices'] = get_all_assets_prices(BUY)
            ctx['tether_irt'] = get_tether_irt_price(BUY)

            symbols = list(self.get_queryset().values_list('symbol', flat=True))
            caps = CoinMarketCap.objects.filter(symbol__in=symbols)
            ctx['cap_info'] = {cap.symbol: cap for cap in caps}

        return ctx

    def get_serializer_option(self, key: str):
        options = {
            'prices': self.request.query_params.get('prices') == '1'
        }

        return options[key]

    def get_serializer_class(self):
        return AssetSerializerBuilder.create_serializer(
            prices=self.get_serializer_option('prices')
        )
