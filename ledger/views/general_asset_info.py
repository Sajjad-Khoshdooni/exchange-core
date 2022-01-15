from datetime import datetime, timedelta

from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models import Asset
from ledger.utils.price import get_all_assets_prices, get_tether_irt_price


class AssetSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    irt_price = serializers.SerializerMethodField()
    weekly_trend_url = serializers.SerializerMethodField()
    irt_price_changed_percent_24h = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ('symbol', 'name', 'name_fa', 'image', 'price', 'irt_price', 'weekly_trend_url')

    def get_price(self, asset: Asset):
        prices = self.context['prices']
        return prices[asset.symbol]

    def get_irt_price(self, asset: Asset):
        tether_irt = self.context['tether_irt']
        return self.get_price(asset) * tether_irt

    def get_weekly_trend_url(self, asset: Asset):
        return 'https://cdn.nobitex.ir/charts/%s.png' % asset.symbol.lower()

    def get_irt_price_changed_percent_24h(self, asset: Asset):
        now_price = self.get_irt_price(asset)

        print('now: coin = %s, tether = %s, coin_irt = %s' % (self.get_price(asset), self.context['tether_irt'], now_price))

        prices_yesterday = self.context['prices_yesterday']
        tether_irt_yesterday = self.context['tether_irt_yesterday']

        yesterday_price = prices_yesterday[asset.symbol] * tether_irt_yesterday

        print('yes: coin = %s, tether = %s, coin_irt = %s' % (prices_yesterday[asset.symbol], tether_irt_yesterday, yesterday_price))

        return round((now_price - yesterday_price) / yesterday_price * 100, 2)


class GeneralAssetInfoView(ListAPIView):

    authentication_classes = []
    permission_classes = []
    serializer_class = AssetSerializer
    queryset = Asset.objects.all()

    def get_serializer_context(self):
        ctx = super(GeneralAssetInfoView, self).get_serializer_context()
        ctx['prices'] = get_all_assets_prices()
        ctx['tether_irt'] = get_tether_irt_price()

        yesterday = datetime.now() - timedelta(days=1)

        ctx['prices_yesterday'] = get_all_assets_prices(now=yesterday)
        ctx['tether_irt_yesterday'] = get_tether_irt_price(now=yesterday)

        return ctx
