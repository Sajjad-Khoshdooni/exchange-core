from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet, DepositAddress, Transfer, OTCTrade, NetworkAsset
from ledger.models.asset import Asset
from ledger.utils.price import get_trading_price_irt


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
        return str(int(get_trading_price_irt(asset.symbol, 'sell')))

    def get_buy_price_irt(self, asset: Asset):
        if asset.is_cash():
            return ''

        return str(int(get_trading_price_irt(asset.symbol, 'buy')))

    class Meta:
        model = Asset
        fields = ('symbol', 'balance', 'balance_irt', 'balance_usdt', 'sell_price_irt', 'buy_price_irt')


class TransferSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()

    def get_link(self, transfer: Transfer):
        return transfer.get_explorer_link()

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
        return addresses.get(network_asset.network.schema.symbol)

    def get_min_withdraw(self, network_asset: NetworkAsset):
        return network_asset.asset.get_presentation_amount(network_asset.min_withdraw)

    def get_withdraw_commission(self, network_asset: NetworkAsset):
        return network_asset.asset.get_presentation_amount(network_asset.withdraw_commission)

    class Meta:
        fields = ('network', 'address', 'can_deposit', 'can_withdraw', 'withdraw_commission', 'min_withdraw')
        model = NetworkAsset


class AssetRetrieveSerializer(AssetListSerializer):

    networks = serializers.SerializerMethodField()
    withdraws = serializers.SerializerMethodField()
    deposits = serializers.SerializerMethodField()
    trades = serializers.SerializerMethodField()

    def get_networks(self, asset: Asset):
        network_assets = asset.networkasset_set.all()

        account = self.context['request'].user.account
        addresses = dict(DepositAddress.objects.filter(account=account).values_list('schema__symbol', 'address'))

        serializer = NetworkAssetSerializer(network_assets, many=True, context={
            'addresses': addresses,
        })

        return serializer.data

    def get_deposits(self, asset: Asset):
        wallet = self.get_wallet(asset)
        deposits = Transfer.objects.filter(wallet=wallet, deposit=True, status=Transfer.DONE)

        return TransferSerializer(instance=deposits, many=True).data

    def get_withdraws(self, asset: Asset):
        wallet = self.get_wallet(asset)
        withdraws = Transfer.objects.filter(wallet=wallet, deposit=False)

        return TransferSerializer(instance=withdraws, many=True).data

    def get_trades(self, asset: Asset):
        wallet = self.get_wallet(asset)
        trades = OTCTrade.objects.filter(lock__wallet=wallet)
        result = []

        for trade in trades:
            config = trade.otc_request.get_trade_config()

            result.append({
                'created': trade.created,
                'side': config.side,
                'amount': config.coin_amount,
                'pair': config.cash.symbol,
                'pair_amount': config.cash_amount
            })

        return result

    class Meta(AssetListSerializer.Meta):
        fields = (*AssetListSerializer.Meta.fields, 'networks', 'deposits', 'withdraws', 'trades')


class WalletView(ModelViewSet):
    queryset = Asset.objects.all().order_by('id')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        market = self.get_market()
        wallets = Wallet.objects.filter(account__user=self.request.user, market=market)
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
        queryset = super(WalletView, self).get_queryset()

        if self.get_market() == Wallet.MARGIN:
            return queryset.exclude(symbol=Asset.IRT)
        else:
            return queryset

    def get_market(self) -> str:
        mapping = {
            'spot': Wallet.SPOT,
            'margin': Wallet.MARGIN
        }

        return mapping.get(self.request.query_params.get('market'), Wallet.SPOT)
