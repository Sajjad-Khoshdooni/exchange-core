from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet, DepositAddress, Transfer, NetworkAsset
from ledger.models.asset import Asset
from ledger.utils.price import get_trading_price_irt, BUY, SELL
from ledger.utils.price_manager import PriceManager
from wallet.utils import get_presentation_address


class AssetListSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    balance_irt = serializers.SerializerMethodField()
    balance_usdt = serializers.SerializerMethodField()
    sell_price_irt = serializers.SerializerMethodField()
    buy_price_irt = serializers.SerializerMethodField()
    can_deposit = serializers.SerializerMethodField()

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

        amount = wallet.get_free_usdt()
        return asset.get_presentation_price_usdt(amount)

    def get_balance_irt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        amount = wallet.get_free_irt()
        return asset.get_presentation_price_irt(amount)

    def get_sell_price_irt(self, asset: Asset):
        if asset.symbol == asset.IRT:
            return ''

        price = get_trading_price_irt(asset.symbol, SELL)
        return asset.get_presentation_price_irt(price)

    def get_buy_price_irt(self, asset: Asset):
        if asset.symbol == asset.IRT:
            return ''

        price = get_trading_price_irt(asset.symbol, BUY)
        return asset.get_presentation_price_irt(price)

    def get_can_deposit(self, asset: Asset):
        return NetworkAsset.objects.filter(asset=asset, network__can_deposit=True).exists()

    class Meta:
        model = Asset
        fields = ('symbol', 'precision', 'balance', 'balance_irt', 'balance_usdt', 'sell_price_irt', 'buy_price_irt', 'can_deposit')


class TransferSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    out_address = serializers.SerializerMethodField()

    def get_link(self, transfer: Transfer):
        return transfer.get_explorer_link()

    def get_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.amount)

    def get_out_address(self, transfer: Transfer):
        return get_presentation_address(transfer.out_address, transfer.network.symbol)

    class Meta:
        model = Transfer
        fields = ('created', 'amount', 'status', 'link', 'out_address')


class NetworkAssetSerializer(serializers.ModelSerializer):
    network = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    can_deposit = serializers.SerializerMethodField()
    can_withdraw = serializers.SerializerMethodField()

    withdraw_commission = serializers.SerializerMethodField()
    min_withdraw = serializers.SerializerMethodField()

    def get_network(self, network_asset: NetworkAsset):
        return network_asset.network.symbol

    def get_can_deposit(self, network_asset: NetworkAsset):
        return network_asset.network.can_deposit

    def get_can_withdraw(self, network_asset: NetworkAsset):
        return network_asset.network.can_withdraw

    def get_address(self, network_asset: NetworkAsset):
        addresses = self.context['addresses']
        return addresses.get(network_asset.network.symbol)

    def get_min_withdraw(self, network_asset: NetworkAsset):
        return network_asset.asset.get_presentation_amount(network_asset.withdraw_min)

    def get_withdraw_commission(self, network_asset: NetworkAsset):
        return network_asset.asset.get_presentation_amount(network_asset.withdraw_fee)

    class Meta:
        fields = ('network', 'address', 'can_deposit', 'can_withdraw', 'withdraw_commission', 'min_withdraw')
        model = NetworkAsset


class AssetRetrieveSerializer(AssetListSerializer):

    networks = serializers.SerializerMethodField()
    withdraws = serializers.SerializerMethodField()
    deposits = serializers.SerializerMethodField()

    def get_networks(self, asset: Asset):
        network_assets = asset.networkasset_set.all()

        account = self.context['request'].user.account

        deposit_addresses = DepositAddress.objects.filter(account_secret__account=account)

        address_mapping = {
            deposit.network.symbol: deposit.presentation_address for deposit in deposit_addresses
        }

        serializer = NetworkAssetSerializer(network_assets, many=True, context={
            'addresses': address_mapping,
        })

        return serializer.data

    def get_deposits(self, asset: Asset):
        wallet = self.get_wallet(asset)
        deposits = Transfer.objects.filter(wallet=wallet, deposit=True, status=Transfer.DONE).order_by('-created')

        return TransferSerializer(instance=deposits, many=True).data

    def get_withdraws(self, asset: Asset):
        wallet = self.get_wallet(asset)
        withdraws = Transfer.objects.filter(wallet=wallet, deposit=False).order_by('-created')

        return TransferSerializer(instance=withdraws, many=True).data

    class Meta(AssetListSerializer.Meta):
        fields = (*AssetListSerializer.Meta.fields, 'networks', 'deposits', 'withdraws')


class WalletViewSet(ModelViewSet):
    queryset = Asset.live_objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        market = self.get_market()
        wallets = Wallet.objects.filter(account=self.request.user.account, market=market)
        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}

        return ctx

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        else:
            return AssetRetrieveSerializer

    def get_object(self):
        return get_object_or_404(Asset, symbol=self.kwargs['symbol'].upper())

    def get_queryset(self):
        queryset = super(WalletViewSet, self).get_queryset()

        if self.get_market() == Wallet.MARGIN:
            return queryset.exclude(symbol=Asset.IRT)
        else:
            return queryset

    def get_market(self) -> str:
        return self.request.query_params.get('market') or Wallet.SPOT

    def list(self, request, *args, **kwargs):
        with PriceManager():
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            wallets = list(filter(lambda w: w['balance'] != '0', data)) + list(filter(lambda w: w['balance'] == '0', data))

        return Response(wallets)


class WalletBalanceView(APIView):

    def get(self, request, *args, **kwargs):
        asset = get_object_or_404(Asset, symbol=kwargs['symbol'].upper())
        wallet = asset.get_wallet(request.user.account)

        return Response({
            'symbol': asset.symbol,
            'balance': wallet.asset.get_presentation_amount(wallet.get_free()),
        })
