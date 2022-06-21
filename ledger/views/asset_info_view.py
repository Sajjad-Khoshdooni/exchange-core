import time
from decimal import Decimal

from django.db.models import Min
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from collector.models import CoinMarketCap
from ledger.models import Asset, Wallet, NetworkAsset, CoinCategory
from ledger.models.asset import AssetSerializerMini
from ledger.utils.fields import get_irt_market_assets
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

    change_7d = serializers.SerializerMethodField()
    high_24h = serializers.SerializerMethodField()
    low_24h = serializers.SerializerMethodField()
    change_1h = serializers.SerializerMethodField()

    cmc_rank = serializers.SerializerMethodField()
    market_cap = serializers.SerializerMethodField()
    circulating_supply = serializers.SerializerMethodField()
    min_withdraw_amount = serializers.SerializerMethodField()
    min_withdraw_fee = serializers.SerializerMethodField()
    market_irt_enable = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ()

    def get_market_irt_enable(self, asset: Asset):
        return asset.id in self.context['enable_irt_market_list']

    def get_bookmark_assets(self, asset: Asset):
        return asset.id in self.context['bookmark_assets']

    def get_cap(self, asset) -> CoinMarketCap:
        return self.context['cap_info'].get(asset.symbol)

    def get_price_usdt(self, asset: Asset):
        prices = self.context['prices']
        price = prices[asset.symbol]
        if not price:
            return

        return asset.get_presentation_price_usdt(price)

    def get_price_irt(self, asset: Asset):
        prices = self.context['prices']
        price = prices[asset.symbol]
        if not price:
            return

        tether_irt = self.context['tether_irt']
        price = price * tether_irt
        return asset.get_presentation_price_irt(price)

    def get_min_withdraw_amount(self, asset: Asset):
        network_assets = NetworkAsset.objects.filter(asset=asset, network__can_withdraw=True)
        min_withdraw = network_assets.aggregate(min=Min('withdraw_min'))
        return min_withdraw['min']

    def get_min_withdraw_fee(self, asset: Asset):
        network_assets = NetworkAsset.objects.filter(asset=asset, network__can_withdraw=True)
        min_withdraw = network_assets.aggregate(min=Min('withdraw_fee'))
        return min_withdraw['min']

    def get_trend_url(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return 'https://s3.coinmarketcap.com/generated/sparklines/web/1d/2781/%d.svg?v=%s' % \
                   (cap.internal_id, str(int(time.time()) // 3600))
        else:
            return '/'

    def get_change_24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.change_24h

    def get_volume_24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return int(cap.volume_24h)

    def get_change_7d(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.change_7d

    def get_high_24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return asset.get_presentation_price_usdt(Decimal(cap.high_24h))

    def get_low_24h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return asset.get_presentation_price_usdt(Decimal(cap.low_24h))

    def get_change_1h(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.change_1h

    def get_cmc_rank(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return int(cap.cmc_rank)

    def get_market_cap(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return cap.market_cap

    def get_circulating_supply(self, asset: Asset):
        cap = self.get_cap(asset)

        if cap:
            return int(cap.circulating_supply)

    @classmethod
    def create_serializer(cls,  prices: bool = True, extra_info: bool = True):
        fields = AssetSerializerMini.Meta.fields
        new_fields = []

        if prices:
            new_fields = ['price_usdt', 'price_irt', 'trend_url', 'change_24h', 'volume_24h', 'market_irt_enable']

        if extra_info:
            new_fields = [
                'price_usdt', 'price_irt', 'change_1h', 'change_24h', 'change_7d',
                'cmc_rank', 'market_cap', 'volume_24h', 'circulating_supply', 'high_24h',
                'low_24h', 'trend_url', 'min_withdraw_amount', 'min_withdraw_fee',
            ]

        class Serializer(cls):
            pass

        Serializer.Meta.fields = (*fields, *new_fields)

        return Serializer


@method_decorator(cache_page(20), name='dispatch')
class AssetsViewSet(ModelViewSet):

    authentication_classes = ()
    permission_classes = ()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['margin_enable']

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        if self.request.user.is_authenticated:
            ctx['bookmark_assets'] = set(self.request.user.account.bookmark_assets.values_list('id', flat=True))
        else:
            ctx['bookmark_assets'] = set()

        ctx['enable_irt_market_list'] = get_irt_market_assets()

        if self.get_options('prices') or self.get_options('extra_info'):
            symbols = list(self.get_queryset().values_list('symbol', flat=True))

            symbol_translation_reversed = {v: k for (k, v) in CoinMarketCap.SYMBOL_TRANSLATION.items()}

            to_search_symbols = list(map(lambda s: symbol_translation_reversed.get(s, s), symbols))
            caps = CoinMarketCap.objects.filter(symbol__in=to_search_symbols)
            ctx['cap_info'] = {CoinMarketCap.SYMBOL_TRANSLATION.get(cap.symbol, cap.symbol): cap for cap in caps}

            ctx['prices'] = get_prices_dict(coins=symbols, side=BUY)
            ctx['tether_irt'] = get_tether_irt_price(BUY)

        return ctx

    def get_options(self, key: str):
        options = {
            'coin': self.request.query_params.get('coin') == '1',
            'prices': self.request.query_params.get('prices') == '1',
            'trend': self.request.query_params.get('trend') == '1',
            'extra_info': self.request.query_params.get('extra_info') == '1',
            'market': self.request.query_params.get('market'),
            'category': self.request.query_params.get('category')
        }

        return options[key]

    def get_serializer_class(self):
        print(self.get_options('extra_info'))
        return AssetSerializerBuilder.create_serializer(
            prices=self.get_options('prices'),
            extra_info=self.get_options('extra_info')
        )

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = Asset.candid_objects.all()
        else:
            queryset = Asset.live_objects.all()

        queryset = queryset.filter(trade_enable=True)

        if self.get_options('category'):
            category = get_object_or_404(CoinCategory, name=self.get_options('category'))
            queryset = queryset.filter(coincategory=category)

        if self.get_options('trend'):
            queryset = queryset.filter(trend=True)

        if self.get_options('market') == Wallet.MARGIN:
            queryset = queryset.filter(margin_enable=True)

        if self.get_options('coin'):
            queryset = queryset.exclude(symbol=Asset.IRT)

        return queryset

    def get_object(self):
        asset = self.get_queryset().filter(symbol=self.kwargs['symbol'].upper(), enable=True).first()

        if not asset:
            raise Http404()

        return asset

    def get(self, *args, **kwargs):
        with PriceManager():
            return super().get(*args, **kwargs)
