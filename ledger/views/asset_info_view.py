from decimal import Decimal

from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from collector.models import CoinMarketCap
from ledger.models import Asset
from ledger.models.asset import AssetSerializerMini
from ledger.utils.price import get_tether_irt_price, BUY, get_prices_dict
from ledger.utils.price_manager import PriceManager


class AssetSerializerBuilder(AssetSerializerMini):
    price_usdt = serializers.SerializerMethodField()
    price_irt = serializers.SerializerMethodField()
    trend_url = serializers.SerializerMethodField()
    irt_price_changed_percent_24h = serializers.SerializerMethodField()
    is_cash = serializers.SerializerMethodField()
    change_24h = serializers.SerializerMethodField()
    volume_24h = serializers.SerializerMethodField()

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

    def get_trend_url(self, asset: Asset):
        cap = CoinMarketCap.objects.filter(symbol=asset.symbol).first()
        if cap:
            return 'https://s3.coinmarketcap.com/generated/sparklines/web/1d/2781/%d.svg' % cap.internal_id
        else:
            return '/'

    def get_change_24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.change_24h

    def get_volume_24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return asset.get_presentation_amount(Decimal(cap.volume_24h))

    def get_cap(self, asset) -> CoinMarketCap:
        return self.context['cap_info'].get(asset.symbol)

    @classmethod
    def create_serializer(cls,  prices: bool = True):
        fields = AssetSerializerMini.Meta.fields
        new_fields = []

        if prices:
            new_fields = ['price_usdt', 'price_irt', 'trend_url', 'change_24h', 'volume_24h']

        class Serializer(cls):
            pass

        Serializer.Meta.fields = (*fields, *new_fields)

        return Serializer


class AssetsViewSet(ModelViewSet):

    authentication_classes = []
    permission_classes = []

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        if self.get_options('prices'):
            symbols = list(self.get_queryset().values_list('symbol', flat=True))
            caps = CoinMarketCap.objects.filter(symbol__in=symbols)
            ctx['cap_info'] = {cap.symbol: cap for cap in caps}

            ctx['prices'] = get_prices_dict(coins=symbols, side=BUY)
            ctx['tether_irt'] = get_tether_irt_price(BUY)

        return ctx

    def get_options(self, key: str):
        options = {
            'prices': self.request.query_params.get('prices') == '1',
            'trend': self.request.query_params.get('trend') == '1'
        }

        return options[key]

    def get_serializer_class(self):
        return AssetSerializerBuilder.create_serializer(
            prices=self.get_options('prices'),
        )

    def get_queryset(self):
        queryset = Asset.live_objects.all()

        if self.get_options('trend'):
            queryset = queryset.filter(trend=True)

        return queryset

    def get_object(self):
        return get_object_or_404(Asset, symbol=self.kwargs['symbol'].upper(), enable=True)

    def get(self, *args, **kwargs):
        with PriceManager():
            return super().get(*args, **kwargs)
