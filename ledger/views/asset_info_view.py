from decimal import Decimal

from django.db.models import Min, F, Q
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Asset, Wallet, NetworkAsset, CoinCategory
from ledger.models.asset import AssetSerializerMini
from ledger.utils.coins_info import get_coins_info
from ledger.utils.external_price import SELL
from ledger.utils.fields import get_irt_market_asset_symbols
from ledger.utils.precision import get_symbol_presentation_price, get_presentation_amount
from ledger.utils.price import get_prices, get_coins_symbols, get_price
from ledger.utils.provider import CoinInfo
from multimedia.models import CoinPriceContent


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

    can_deposit = serializers.SerializerMethodField()
    can_withdraw = serializers.SerializerMethodField()

    description = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ()

    def get_market_irt_enable(self, asset: Asset):
        return asset.symbol in self.context['enable_irt_market_list']

    def get_bookmark_assets(self, asset: Asset):
        return asset.id in self.context['bookmark_assets']

    def get_cap(self, asset) -> CoinInfo:
        return self.context['cap_info'].get(asset.symbol, CoinInfo())

    def get_price_usdt(self, asset: Asset):
        price = self.context['prices'].get(asset.symbol + Asset.USDT, 0)
        return get_symbol_presentation_price(asset.symbol + Asset.USDT, price)

    def get_price_irt(self, asset: Asset):
        price = self.context['prices'].get(asset.symbol + Asset.IRT, 0)
        return get_symbol_presentation_price(asset.symbol + Asset.IRT, price)

    def get_min_withdraw_amount(self, asset: Asset):
        network_assets = NetworkAsset.objects.filter(asset=asset, network__can_withdraw=True, can_withdraw=True)
        min_withdraw = network_assets.aggregate(min=Min('withdraw_min'))
        return min_withdraw['min']

    def get_min_withdraw_fee(self, asset: Asset):
        network_assets = NetworkAsset.objects.filter(asset=asset, network__can_withdraw=True, can_withdraw=True)
        min_withdraw = network_assets.aggregate(min=Min('withdraw_fee'))
        return min_withdraw['min']

    def get_trend_url(self, asset: Asset):
        return ''
        return self.get_cap(asset).weekly_trend_url

    def get_change_24h(self, asset: Asset):
        return self.get_cap(asset).change_24h

    def get_volume_24h(self, asset: Asset):
        return self.get_cap(asset).volume_24h

    def get_change_7d(self, asset: Asset):
        return self.get_cap(asset).change_7d

    def get_high_24h(self, asset: Asset):
        cap = self.get_cap(asset)
        return get_symbol_presentation_price(asset.symbol + 'USDT',  Decimal(cap.high_24h))

    def get_low_24h(self, asset: Asset):
        cap = self.get_cap(asset)
        return get_symbol_presentation_price(asset.symbol + 'USDT', Decimal(cap.low_24h))

    def get_change_1h(self, asset: Asset):
        return self.get_cap(asset).change_1h

    def get_cmc_rank(self, asset: Asset):
        return self.get_cap(asset).cmc_rank

    def get_market_cap(self, asset: Asset):
        return self.get_cap(asset).market_cap

    def get_circulating_supply(self, asset: Asset):
        return self.get_cap(asset).circulating_supply

    def get_can_deposit(self, asset: Asset):
        return NetworkAsset.objects.filter(
            asset=asset,
            can_deposit=True,
            hedger_deposit_enable=True,
            network__can_deposit=True
        ).exists()

    def get_can_withdraw(self, asset: Asset):
        return NetworkAsset.objects.filter(
            asset=asset,
            can_withdraw=True,
            hedger_withdraw_enable=True,
            network__can_withdraw=True
        ).exists()

    def get_description(self, asset: Asset):
        content = CoinPriceContent.objects.filter(asset=asset).first()
        if content:
            return content.get_html()

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
                'low_24h', 'trend_url', 'min_withdraw_amount', 'min_withdraw_fee', 'can_deposit', 'can_withdraw',
                'market_irt_enable', 'description',
            ]

        class Serializer(cls):
            pass

        Serializer.Meta.fields = (*fields, *new_fields)

        return Serializer


@method_decorator(cache_page(10), name='dispatch')
class AssetsViewSet(ModelViewSet):

    authentication_classes = ()
    permission_classes = ()
    filter_backends = [DjangoFilterBackend]

    def get_serializer_context(self):

        ctx = super().get_serializer_context()

        if self.request.user.is_authenticated:
            ctx['bookmark_assets'] = set(self.request.user.get_account().bookmark_assets.values_list('id', flat=True))
        else:
            ctx['bookmark_assets'] = set()

        ctx['enable_irt_market_list'] = get_irt_market_asset_symbols()

        if self.get_options('prices') or self.get_options('extra_info'):
            coins = list(self.get_queryset().values_list('symbol', flat=True))
            ctx['cap_info'] = get_coins_info()
            ctx['prices'] = get_prices(get_coins_symbols(coins), side=SELL, allow_stale=True)

        return ctx

    def get_options(self, key: str):
        options = {
            'coin': self.request.query_params.get('coin') == '1',
            'prices': self.request.query_params.get('prices') == '1',
            'trend': self.request.query_params.get('trend') == '1',
            'extra_info': self.request.query_params.get('extra_info') == '1',
            'market': self.request.query_params.get('market'),
            'category': self.request.query_params.get('category'),
            'name': self.request.query_params.get('name'),
            'can_deposit': self.request.query_params.get('can_deposit') == '1',
            'can_withdraw': self.request.query_params.get('can_withdraw') == '1',
            'is_base': self.request.query_params.get('is_base') == '1',
            'active': self.request.query_params.get('active') == '1',
        }

        return options[key]

    def get_serializer_class(self):
        return AssetSerializerBuilder.create_serializer(
            prices=self.get_options('prices'),
            extra_info=self.get_options('extra_info')
        )

    def get_queryset(self):
        if self.get_options('extra_info') and not self.get_options('active'):
            queryset = Asset.objects.filter(Q(enable=True) | Q(price_page=True))
        else:
            queryset = Asset.live_objects.all()

        if self.get_options('category'):
            category_name = self.get_options('category')

            if category_name == 'new-coins':
                queryset = queryset.order_by(F('publish_date').desc(nulls_last=True))[:100]
            else:
                category = get_object_or_404(CoinCategory, name=category_name)
                queryset = queryset.filter(coincategory=category)

        if self.get_options('is_base'):
            queryset = queryset.filter(symbol__in=(Asset.IRT, Asset.USDT))

        if self.get_options('trend'):
            queryset = queryset.filter(trend=True)

        if self.get_options('coin'):
            queryset = queryset.exclude(symbol=Asset.IRT)

        if self.get_options('name'):
            queryset = queryset.filter(name=self.get_options('name'))

        if self.get_options('can_deposit'):
            queryset = queryset.filter(
                networkasset__can_deposit=True,
                networkasset__network__can_deposit=True
            ).distinct()

        if self.get_options('can_withdraw'):
            queryset = queryset.filter(
                networkasset__can_withdraw=True,
                networkasset__network__can_withdraw=True
            ).distinct()

        return queryset

    def get_object(self):
        asset = self.get_queryset().filter(symbol=self.kwargs['symbol'].upper(), enable=True).first()

        if not asset:
            raise Http404()

        return asset


class AssetOverviewAPIView(APIView):
    permission_classes = []

    @classmethod
    def set_price(cls, assets_info: list):
        for asset_info in assets_info:
            coin = asset_info['symbol']

            asset_info['price_usdt'] = get_symbol_presentation_price(
                symbol=coin + Asset.USDT,
                amount=get_price(coin + Asset.USDT, side=SELL, allow_stale=True) or 0
            )

            asset_info['price_irt'] = get_symbol_presentation_price(
                symbol=coin + Asset.IRT,
                amount=get_price(coin + Asset.IRT, side=SELL, allow_stale=True) or 0
            )

            asset_info['market_irt_enable'] = coin in get_irt_market_asset_symbols()
            asset_info.update(AssetSerializerMini(Asset.get(symbol=coin)).data)

    def get(self, request):
        limit = int(self.request.query_params.get('limit', default=3))

        coins = set(Asset.live_objects.filter(
            otc_status=Asset.ACTIVE
        ).exclude(symbol=Asset.IRT).values_list('symbol', flat=True))

        caps_dict = {c: cap for (c, cap) in get_coins_info().items() if c in coins}
        caps = caps_dict.values()

        def coin_info_to_dict(info: CoinInfo):
            return {
                'symbol': info.coin,
                'change_24h': info.change_24h,
                'volume_24h': info.volume_24h,
                'trend_url': info.weekly_trend_url,
            }

        high_volume = list(map(coin_info_to_dict, sorted(caps, key=lambda cap: cap.volume_24h, reverse=True)[:limit]))
        AssetOverviewAPIView.set_price(high_volume)

        high_24h_change = list(map(coin_info_to_dict, sorted(caps, key=lambda cap: cap.change_24h, reverse=True)[:limit]))
        AssetOverviewAPIView.set_price(high_24h_change)

        newest_coin_symbols = list(Asset.live_objects.filter(symbol__in=caps_dict, otc_status=Asset.ACTIVE).exclude(
            symbol__in=['IRT', 'IOTA']
        ).order_by(F('publish_date').desc(nulls_last=True)).values_list('symbol', flat=True))[:limit]

        newest = list(map(coin_info_to_dict, map(lambda coin: caps_dict[coin], newest_coin_symbols)))
        AssetOverviewAPIView.set_price(newest)

        return Response({
            'high_volume': high_volume,
            'high_24h_change': high_24h_change,
            'newest': newest
        })


class MarginAssetInterestSerializer(AssetSerializerMini):
    margin_interest_fee = serializers.SerializerMethodField()

    def get_margin_interest_fee(self, asset: Asset):
        return get_presentation_amount(asset.margin_interest_fee * 100)

    class Meta:
        model = Asset
        fields = (*AssetSerializerMini.Meta.fields, 'symbol', 'margin_interest_fee',)


class MarginAssetInterestView(ListAPIView):
    permission_classes = []
    serializer_class = MarginAssetInterestSerializer
    queryset = Asset.objects.filter(
        Q(pair__margin_enable=True) | Q(symbol__in=[Asset.IRT, Asset.USDT])
    ).distinct().order_by('id')
    pagination_class = LimitOffsetPagination
    search_fields = ['symbol', 'name', 'name_fa']
    filter_backends = [DjangoFilterBackend, SearchFilter]
