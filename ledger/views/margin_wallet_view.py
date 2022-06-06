from decimal import Decimal

from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet, DepositAddress, Transfer, NetworkAsset, Network
from ledger.models.asset import Asset
from ledger.utils.precision import get_presentation_amount
from ledger.utils.price import get_trading_price_irt, BUY, SELL, get_prices_dict
from ledger.utils.price_manager import PriceManager
from rest_framework.generics import ListAPIView


class MarginAssetListSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    balance_usdt = serializers.SerializerMethodField()
    free = serializers.SerializerMethodField()
    borrowed = serializers.SerializerMethodField()
    equity = serializers.SerializerMethodField()

    def get_wallet(self, asset: Asset):
        return self.context['asset_to_wallet'].get(asset.id)

    def get_loan_wallet(self, asset: Asset):
        return self.context['asset_to_loan'].get(asset.id)

    def get_balance(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return asset.get_presentation_amount(wallet.get_balance())

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

    def get_borrowed(self, asset: Asset):
        loan = self.get_loan_wallet(asset)

        if not loan:
            return '0'

        return asset.get_presentation_amount(-loan.get_balance())

    def get_equity(self, asset: Asset):
        wallet = self.get_wallet(asset)
        loan = self.get_loan_wallet(asset)

        if wallet:
            wallet_value = wallet.get_balance()
        else:
            wallet_value = 0

        if loan:
            loan_value = loan.get_balance()
        else:
            loan_value = 0

        return asset.get_presentation_amount(loan_value + wallet_value)

    class Meta:
        model = Asset
        fields = ('symbol', 'free', 'balance', 'balance_usdt', 'borrowed', 'equity')
        ref_name = 'margin wallets'


class MarginWalletViewSet(ModelViewSet):
    serializer_class = MarginAssetListSerializer
    queryset = Asset.live_objects.filter(margin_enable=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        account = self.request.user.account
        wallets = Wallet.objects.filter(account=account, market=Wallet.MARGIN)
        loans = Wallet.objects.filter(account=account, market=Wallet.LOAN)

        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}
        ctx['asset_to_loan'] = {wallet.asset_id: wallet for wallet in loans}

        return ctx
