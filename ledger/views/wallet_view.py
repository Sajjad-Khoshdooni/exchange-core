import decimal

from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models import Wallet, NetworkAsset
from ledger.models.asset import AssetSerializerMini, Asset
from ledger.models.network import NetworkSerializer, Network
from ledger.utils.price import get_all_assets_prices, get_tether_irt_price


class WalletSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    balance_irt = serializers.SerializerMethodField()
    balance_usdt = serializers.SerializerMethodField()
    networks = serializers.SerializerMethodField()
    asset = AssetSerializerMini()

    def get_symbol(self, wallet: Wallet):
        return wallet.asset.symbol

    def get_balance(self, wallet: Wallet):
        balance = round(wallet.get_balance(), 6)
        return str(balance).rstrip('0').rstrip('.')

    def get_balance_usdt(self, wallet: Wallet):
        return str(int(wallet.get_balance_usdt()))

    def get_balance_irt(self, wallet: Wallet):
        return str(int(wallet.get_balance_irt()))

    def get_networks(self, wallet: Wallet):
        network_ids = NetworkAsset.objects.filter(asset=wallet.asset).values_list('id', flat=True)
        networks = Network.objects.filter(id__in=network_ids)
        return NetworkSerializer(instance=networks, many=True).data

    class Meta:
        model = Wallet
        fields = ('id', 'asset', 'balance', 'balance_irt', 'balance_usdt', 'networks')


class WalletView(ListAPIView):
    serializer_class = WalletSerializer

    def get_queryset(self):
        return Wallet.objects.filter(account__user=self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        if self.request.method == 'GET':
            ctx['prices'] = get_all_assets_prices()
            ctx['tether_irt'] = get_tether_irt_price()

        return ctx
