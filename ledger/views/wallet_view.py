from decimal import Decimal

from django.conf import settings
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet, DepositAddress, NetworkAsset, OTCRequest, OTCTrade
from ledger.models.asset import Asset
from ledger.utils.fields import get_irt_market_asset_symbols
from ledger.utils.precision import get_presentation_amount, get_precision
from ledger.utils.price import get_trading_price_irt, BUY, SELL
from ledger.utils.price_manager import PriceManager
import logging

logger = logging.getLogger(__name__)


class AssetListSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    balance = serializers.SerializerMethodField()
    balance_irt = serializers.SerializerMethodField()
    balance_usdt = serializers.SerializerMethodField()

    sell_price_irt = serializers.SerializerMethodField()
    buy_price_irt = serializers.SerializerMethodField()
    can_deposit = serializers.SerializerMethodField()
    can_withdraw = serializers.SerializerMethodField()

    free = serializers.SerializerMethodField()
    free_irt = serializers.SerializerMethodField()

    pin_to_top = serializers.SerializerMethodField()

    precision = serializers.SerializerMethodField()

    market_irt_enable = serializers.SerializerMethodField()

    original_name_fa = serializers.SerializerMethodField()
    original_symbol = serializers.SerializerMethodField()

    step_size = serializers.SerializerMethodField()

    def get_market_irt_enable(self, asset: Asset):
        return asset.symbol in self.context['enable_irt_market_list']

    def get_precision(self, asset: Asset):
        return asset.get_precision()

    def get_pin_to_top(self, asset: Asset):
        return asset.pin_to_top

    def get_wallet(self, asset: Asset):
        return self.context['asset_to_wallet'].get(asset.id)

    def get_balance(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return asset.get_presentation_amount(wallet.get_balance())

    def get_balance_irt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        amount = wallet.get_balance_irt()
        return asset.get_presentation_price_irt(amount)

    def get_balance_usdt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        amount = wallet.get_balance_usdt()
        return asset.get_presentation_price_usdt(amount)

    def get_free(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return asset.get_presentation_amount(wallet.get_free())

    def get_free_irt(self, asset: Asset):
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
        if asset.symbol == Asset.IRT:
            return True

        network_asset = NetworkAsset.objects.filter(asset=asset, network__can_deposit=True).first()
        return bool(network_asset and network_asset.can_deposit_enabled())

    def get_can_withdraw(self, asset: Asset):
        if asset.symbol == Asset.IRT:
            return True

        return NetworkAsset.objects.filter(
            asset=asset,
            network__can_withdraw=True,
            hedger_withdraw_enable=True,
            can_withdraw=True,
        ).exists()

    def get_logo(self, asset: Asset):
        return settings.HOST_URL + '/static/coins/%s.png' % asset.symbol

    def get_original_symbol(self, asset: Asset):
        return asset.original_symbol or asset.symbol

    def get_original_name_fa(self, asset: Asset):
        return asset.original_name_fa or asset.name_fa

    def get_step_size(self, asset: Asset):
        return get_precision(asset.trade_quantity_step)

    class Meta:
        model = Asset
        fields = ('symbol', 'precision', 'free', 'free_irt', 'balance', 'balance_irt', 'balance_usdt', 'sell_price_irt',
                  'buy_price_irt', 'can_deposit', 'can_withdraw', 'trade_enable', 'pin_to_top', 'market_irt_enable',
                  'name', 'name_fa', 'logo', 'original_symbol', 'original_name_fa', 'step_size')
        ref_name = 'ledger asset'


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

    need_memo = serializers.SerializerMethodField()

    def get_need_memo(self, network_asset: NetworkAsset):
        return network_asset.network.need_memo

    def get_network(self, network_asset: NetworkAsset):
        return network_asset.network.symbol

    def get_network_name(self, network_asset: NetworkAsset):
        return network_asset.network.name

    def get_address_regex(self, network_asset: NetworkAsset):
        return network_asset.network.address_regex

    def get_can_deposit(self, network_asset: NetworkAsset):
        return network_asset.can_deposit_enabled()

    def get_can_withdraw(self, network_asset: NetworkAsset):
        return network_asset.can_withdraw_enabled()

    def get_address(self, network_asset: NetworkAsset):
        addresses = self.context.get('addresses', {})
        return addresses.get(network_asset.network.symbol)

    def get_min_withdraw(self, network_asset: NetworkAsset):
        return get_presentation_amount(network_asset.withdraw_min)

    def get_withdraw_commission(self, network_asset: NetworkAsset):
        return get_presentation_amount(network_asset.withdraw_fee)

    def get_withdraw_precision(self, network_asset: NetworkAsset):
        return network_asset.withdraw_precision

    class Meta:
        fields = ('network', 'address', 'can_deposit', 'can_withdraw', 'withdraw_commission', 'min_withdraw',
                  'network_name', 'address_regex', 'withdraw_precision', 'need_memo')
        model = NetworkAsset


class AssetRetrieveSerializer(AssetListSerializer):
    networks = serializers.SerializerMethodField()

    def get_networks(self, asset: Asset):
        network_assets = asset.networkasset_set.all().order_by('withdraw_fee')

        account = self.context['request'].user.account

        deposit_addresses = DepositAddress.objects.filter(address_key__account=account)

        address_mapping = {
            deposit.network.symbol: deposit.address for deposit in deposit_addresses
        }

        serializer = NetworkAssetSerializer(network_assets, many=True, context={
            'addresses': address_mapping,
        })

        return serializer.data

    class Meta(AssetListSerializer.Meta):
        fields = (*AssetListSerializer.Meta.fields, 'networks')


class WalletViewSet(ModelViewSet):

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        wallets = Wallet.objects.filter(account=self.request.user.account, market=Wallet.SPOT, variant__isnull=True)
        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}
        ctx['enable_irt_market_list'] = get_irt_market_asset_symbols()
        return ctx

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        else:
            return AssetRetrieveSerializer

    def get_object(self):
        return get_object_or_404(Asset, symbol=self.kwargs['symbol'].upper())

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Asset.candid_objects.all()
        else:
            return Asset.live_objects.all()

    def list(self, request, *args, **kwargs):
        with PriceManager(fetch_all=True, allow_stale=True):
            queryset = self.get_queryset()

            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            pin_to_top_wallets = list(filter(lambda w: w['pin_to_top'], data))
            with_balance_wallets = list(filter(lambda w: w['balance'] != '0' and not w['pin_to_top'], data))
            without_balance_wallets = list(filter(lambda w: w['balance'] == '0' and not w['pin_to_top'], data))

            wallets = pin_to_top_wallets + sorted(with_balance_wallets, key=lambda w: Decimal(w['balance_irt'] or 0), reverse=True) + without_balance_wallets

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


class BriefNetworkAssetsSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    symbol = serializers.SerializerMethodField()
    address_regex = serializers.SerializerMethodField()

    def get_name(self, network_asset: NetworkAsset):
        return network_asset.network.name

    def get_symbol(self, network_asset: NetworkAsset):
        return network_asset.network.symbol

    def get_address_regex(self, network_asset: NetworkAsset):
        return network_asset.network.address_regex

    class Meta:
        fields = ('name', 'symbol', 'address_regex')
        model = NetworkAsset


class BriefNetworkAssetsView(ListAPIView):
    serializer_class = BriefNetworkAssetsSerializer

    def get_queryset(self):
        query_params = self.request.query_params
        query_set = NetworkAsset.objects.all()
        if 'symbol' in query_params:
            return query_set.filter(asset__symbol=query_params['symbol'].upper(),
                                    can_withdraw=True,
                                    network__can_withdraw=True,
                                    hedger_withdraw_enable=True)
        else:
            query_set = query_set.distinct('network__symbol')

        return query_set.filter(can_withdraw=True, network__can_withdraw=True, network__is_universal=True)


class WalletSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField()
    free = serializers.SerializerMethodField()

    def get_asset(self, wallet: Wallet):
        return wallet.asset.symbol

    def get_free(self, wallet: Wallet):
        return wallet.asset.get_presentation_amount(wallet.get_free())

    class Meta:
        model = Wallet
        fields = ('asset', 'free',)


class ConvertDustView(APIView):

    def post(self, *args):
        account = self.request.user.account
        IRT = Asset.get(Asset.IRT)
        spot_wallets = Wallet.objects.filter(account=account, market=Wallet.SPOT, balance__gt=0).exclude(asset=IRT)

        for wallet in spot_wallets:
            if Decimal(0) < wallet.get_free_irt() < Decimal('100000'):
                logger.info('Converting dust %s' % wallet)

                request = OTCRequest.new_trade(
                    account=account,
                    market=Wallet.SPOT,
                    from_asset=wallet.asset,
                    to_asset=IRT,
                    from_amount=wallet.get_free(),
                    allow_dust=True
                )

                OTCTrade.execute_trade(request, force=True)

        return Response({'msg': 'convert_dust success'}, status=status.HTTP_200_OK)

