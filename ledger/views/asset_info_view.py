from decimal import Decimal

from django.db.models import Min, F, Q
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Asset, Wallet, NetworkAsset, CoinCategory
from ledger.models.asset import AssetSerializerMini
from ledger.utils.external_price import BUY, get_external_usdt_prices, get_external_price, SELL
from ledger.utils.fields import get_irt_market_asset_symbols
from ledger.utils.provider import CoinInfo, get_provider_requester
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
        price = self.context.get('market_prices', {'USDT': {}})['USDT'].get(asset.symbol, 0)
        if not price:
            price = self.context.get('prices', {}).get(asset.symbol, 0)
        if not price:
            return

        return asset.get_presentation_price_usdt(price)

    def get_price_irt(self, asset: Asset):
        price = self.context.get('market_prices', {'IRT': {}})['IRT'].get(asset.symbol, 0)
        if price:
            return asset.get_presentation_price_irt(price)
        else:
            price = self.context.get('prices', {}).get(asset.symbol, 0)
        if not price:
            return

        tether_irt = self.context['tether_irt']
        price = price * tether_irt
        return asset.get_presentation_price_irt(price)

    def get_min_withdraw_amount(self, asset: Asset):
        network_assets = NetworkAsset.objects.filter(asset=asset, network__can_withdraw=True, can_withdraw=True)
        min_withdraw = network_assets.aggregate(min=Min('withdraw_min'))
        return min_withdraw['min']

    def get_min_withdraw_fee(self, asset: Asset):
        network_assets = NetworkAsset.objects.filter(asset=asset, network__can_withdraw=True, can_withdraw=True)
        min_withdraw = network_assets.aggregate(min=Min('withdraw_fee'))
        return min_withdraw['min']

    def get_trend_url(self, asset: Asset):
        return self.get_cap(asset).weekly_trend_url

    def get_change_24h(self, asset: Asset):
        return self.get_cap(asset).change_24h

    def get_volume_24h(self, asset: Asset):
        return self.get_cap(asset).volume_24h

    def get_change_7d(self, asset: Asset):
        return self.get_cap(asset).change_7d

    def get_high_24h(self, asset: Asset):
        cap = self.get_cap(asset)
        return asset.get_presentation_price_usdt(Decimal(cap.high_24h))

    def get_low_24h(self, asset: Asset):
        cap = self.get_cap(asset)
        return asset.get_presentation_price_usdt(Decimal(cap.low_24h))

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
    filterset_fields = ['margin_enable']

    def get_serializer_context(self):

        ctx = super().get_serializer_context()

        if self.request.user.is_authenticated:
            ctx['bookmark_assets'] = set(self.request.user.get_account().bookmark_assets.values_list('id', flat=True))
        else:
            ctx['bookmark_assets'] = set()

        ctx['enable_irt_market_list'] = get_irt_market_asset_symbols()

        if self.get_options('prices') or self.get_options('extra_info'):
            symbols = list(self.get_queryset().values_list('symbol', flat=True))
            ctx['cap_info'] = get_provider_requester().get_coins_info(symbols)
            ctx['prices'] = get_external_usdt_prices(
                coins=symbols,
                side=BUY,
                allow_stale=True,
                apply_otc_spread=True
            )
            ctx['market_prices'] = {}
            from market.models import Order
            for base_asset in ('IRT', 'USDT'):
                ctx['market_prices'][base_asset] = {
                    o['symbol__name'].replace(base_asset, ''): o['best_ask'] for o in Order.open_objects.filter(
                        side=SELL,
                        symbol__enable=True,
                        symbol__name__in=map(lambda s: f'{s}{base_asset}', symbols)
                    ).values('symbol__name').annotate(best_ask=Min('price'))
                }
            ctx['tether_irt'] = get_external_price(coin=Asset.USDT, base_coin=Asset.IRT, side=BUY, allow_stale=True)

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
        }

        return options[key]

    def get_serializer_class(self):
        return AssetSerializerBuilder.create_serializer(
            prices=self.get_options('prices'),
            extra_info=self.get_options('extra_info')
        )

    def get_queryset(self):
        if self.get_options('extra_info'):
            queryset = Asset.objects.filter(Q(enable=True) | Q(price_page=True))
        else:
            queryset = Asset.live_objects.all()

        if self.get_options('category'):
            category_name = self.get_options('category')

            if category_name == 'new-coins':
                queryset = queryset.order_by(F('publish_date').desc(nulls_last=True))[:25]
            else:
                category = get_object_or_404(CoinCategory, name=category_name)
                queryset = queryset.filter(coincategory=category)

        if self.get_options('trend'):
            queryset = queryset.filter(trend=True)

        if self.get_options('market') == Wallet.MARGIN:
            queryset = queryset.filter(margin_enable=True)

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
    def set_price(cls, coins: list):
        symbols = list(map(lambda c: c['symbol'], coins))
        assets = Asset.objects.filter(symbol__in=symbols)

        asset_map = {a.symbol: a for a in assets}

        for coin in coins:
            symbol = coin['symbol']
            asset = asset_map[symbol]

            coin['price_usdt'] = asset.get_presentation_price_usdt(
                get_external_price(coin=symbol, base_coin=Asset.USDT, side=BUY, allow_stale=True)
            )

            coin['price_irt'] = asset.get_presentation_price_irt(
                get_external_price(coin=symbol, base_coin=Asset.IRT, side=BUY, allow_stale=True)
            )

            coin['market_irt_enable'] = symbol in get_irt_market_asset_symbols()
            coin.update(AssetSerializerMini(Asset.get(symbol=symbol)).data)

    def get(self, request):
        limit = int(self.request.query_params.get('limit', default=3))

        coins = list(Asset.live_objects.filter(
            otc_status=Asset.ACTIVE
        ).exclude(symbol=Asset.IRT).values_list('symbol', flat=True))

        caps = get_provider_requester().get_coins_info(coins).values()
        caps_dict = {c.coin: c for c in caps}

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
