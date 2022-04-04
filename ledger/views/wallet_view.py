from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet, DepositAddress, Transfer, NetworkAsset
from ledger.models.asset import Asset
from ledger.utils.precision import get_presentation_amount
from ledger.utils.price import get_trading_price_irt, BUY, SELL, get_prices_dict
from ledger.utils.price_manager import PriceManager
from wallet.utils import get_presentation_address


class AssetListSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    balance_irt = serializers.SerializerMethodField()
    balance_usdt = serializers.SerializerMethodField()
    sell_price_irt = serializers.SerializerMethodField()
    buy_price_irt = serializers.SerializerMethodField()
    can_deposit = serializers.SerializerMethodField()
    can_withdraw = serializers.SerializerMethodField()

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

    def get_can_withdraw(self, asset: Asset):
        return NetworkAsset.objects.filter(
            asset=asset,
            network__can_withdraw=True,
            binance_withdraw_enable=True
        ).exists()

    class Meta:
        model = Asset
        fields = ('symbol', 'precision', 'balance', 'balance_irt', 'balance_usdt', 'sell_price_irt', 'buy_price_irt',
                  'can_deposit', 'can_withdraw')
        ref_name = 'ledger asset'


class TransferSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()
    coin = serializers.SerializerMethodField()

    def get_link(self, transfer: Transfer):
        return transfer.get_explorer_link()

    def get_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.total_amount - transfer.fee_amount)

    def get_fee_amount(self, transfer: Transfer):
        return transfer.wallet.asset.get_presentation_amount(transfer.fee_amount)

    def get_coin(self, transfer: Transfer):
        return transfer.wallet.asset.symbol

    def get_network(self, transfer: Transfer):
        return transfer.network.symbol

    class Meta:
        model = Transfer
        fields = ('created', 'amount', 'status', 'link', 'out_address', 'coin', 'network', 'trx_hash', 'fee_amount')


class NetworkAssetSerializer(serializers.ModelSerializer):
    network = serializers.SerializerMethodField()
    network_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    can_deposit = serializers.SerializerMethodField()
    can_withdraw = serializers.SerializerMethodField()
    address_regex = serializers.SerializerMethodField()

    withdraw_commission = serializers.SerializerMethodField()
    min_withdraw = serializers.SerializerMethodField()

    withdraw_precision = serializers.SerializerMethodField()

    def get_network(self, network_asset: NetworkAsset):
        return network_asset.network.symbol

    def get_network_name(self, network_asset: NetworkAsset):
        return network_asset.network.name

    def get_address_regex(self, network_asset: NetworkAsset):
        return network_asset.network.address_regex

    def get_can_deposit(self, network_asset: NetworkAsset):
        return network_asset.network.can_deposit

    def get_can_withdraw(self, network_asset: NetworkAsset):
        return network_asset.network.can_withdraw and network_asset.binance_withdraw_enable

    def get_address(self, network_asset: NetworkAsset):
        addresses = self.context['addresses']
        return addresses.get(network_asset.network.symbol)

    def get_min_withdraw(self, network_asset: NetworkAsset):
        return get_presentation_amount(network_asset.withdraw_min)

    def get_withdraw_commission(self, network_asset: NetworkAsset):
        return get_presentation_amount(network_asset.withdraw_fee)

    def get_withdraw_precision(self, network_asset: NetworkAsset):
        return network_asset.withdraw_precision

    class Meta:
        fields = ('network', 'address', 'can_deposit', 'can_withdraw', 'withdraw_commission', 'min_withdraw',
                  'network_name', 'address_regex', 'withdraw_precision')
        model = NetworkAsset


class AssetRetrieveSerializer(AssetListSerializer):

    networks = serializers.SerializerMethodField()

    def get_networks(self, asset: Asset):
        network_assets = asset.networkasset_set.all().order_by('withdraw_fee')

        account = self.context['request'].user.account

        deposit_addresses = DepositAddress.objects.filter(account_secret__account=account)

        address_mapping = {
            deposit.network.symbol: deposit.presentation_address for deposit in deposit_addresses
        }

        serializer = NetworkAssetSerializer(network_assets, many=True, context={
            'addresses': address_mapping,
        })

        return serializer.data

    class Meta(AssetListSerializer.Meta):
        fields = (*AssetListSerializer.Meta.fields, 'networks')


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
            get_prices_dict(coins=list(queryset.values_list('symbol', flat=True)))  # cache prices

            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            wallets = list(filter(lambda w: w['balance'] != '0', data)) + list(filter(lambda w: w['balance'] == '0', data))

        return Response(wallets)


class WalletBalanceView(APIView):

    def get(self, request, *args, **kwargs):
        market = request.query_params.get('market', Wallet.SPOT)
        asset = get_object_or_404(Asset, symbol=kwargs['symbol'].upper())

        wallet = asset.get_wallet(request.user.account, market=market)

        return Response({
            'symbol': asset.symbol,
            'balance': wallet.asset.get_presentation_amount(wallet.get_free()),
        })
