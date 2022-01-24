from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet
from ledger.models.asset import Asset
from ledger.utils.price import get_trading_price


class AssetListSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    balance_irt = serializers.SerializerMethodField()
    balance_usdt = serializers.SerializerMethodField()
    sell_price_irt = serializers.SerializerMethodField()
    buy_price_irt = serializers.SerializerMethodField()

    def get_wallet(self, asset: Asset):
        return self.context['asset_to_wallet'].get(asset.id)

    def get_balance(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return asset.get_presentation_amount(wallet.get_free())

    def get_balance_usdt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return str(int(wallet.get_free_usdt()))

    def get_balance_irt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return str(int(wallet.get_free_irt()))

    def get_sell_price_irt(self, asset: Asset):
        if asset.is_cash():
            return ''
        return str(int(get_trading_price(asset.symbol, 'sell')))

    def get_buy_price_irt(self, asset: Asset):
        if asset.is_cash():
            return ''

        return str(int(get_trading_price(asset.symbol, 'buy')))

    class Meta:
        model = Asset
        fields = ('symbol', 'balance', 'balance_irt', 'balance_usdt', 'sell_price_irt', 'buy_price_irt')


class AssetRetrieveSerializer(AssetListSerializer):

    networks = serializers.SerializerMethodField()

    def get_networks(self, asset: Asset):
        networks = list(asset.networkasset_set.all().values('network__symbol', 'commission'))
        return [{
            'network': net['network__symbol'],
            'commission': asset.get_presentation_amount(net['commission'])
        } for net in networks]

    class Meta(AssetListSerializer.Meta):
        fields = (*AssetListSerializer.Meta.fields, 'networks')


class WalletView(ModelViewSet):
    queryset = Asset.objects.all().order_by('id')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        wallets = Wallet.objects.filter(account__user=self.request.user)
        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}

        return ctx

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        else:
            return AssetRetrieveSerializer

    def get_object(self):
        return get_object_or_404(Asset, symbol=self.kwargs['symbol'].upper())
