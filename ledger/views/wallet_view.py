from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models import Wallet, NetworkAsset
from ledger.models.asset import AssetSerializerMini, Asset
from ledger.models.network import NetworkSerializer, Network
from ledger.utils.price import get_all_assets_prices, get_tether_irt_price, get_trading_price


class AssetSerializer(serializers.ModelSerializer):
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
        return str(int(get_trading_price(asset.symbol, 'sell')))

    def get_buy_price_irt(self, asset: Asset):
        return str(int(get_trading_price(asset.symbol, 'buy')))

    class Meta:
        model = Asset
        fields = ('symbol', 'balance', 'balance_irt', 'balance_usdt', 'sell_price_irt', 'buy_price_irt')


class WalletView(ListAPIView):
    serializer_class = AssetSerializer
    
    def get_queryset(self):
        return Asset.objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        wallets = Wallet.objects.filter(account__user=self.request.user)
        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}

        return ctx
