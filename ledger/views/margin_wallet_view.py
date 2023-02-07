from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet
from ledger.models.asset import Asset, AssetSerializerMini
from ledger.utils.external_price import get_external_price, BUY


class MarginAssetListSerializer(AssetSerializerMini):
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

        return asset.get_presentation_amount(wallet.balance)

    def get_balance_usdt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        price = get_external_price(coin=wallet.asset.symbol, base_coin=Asset.USDT, side=BUY, allow_stale=True)
        amount = wallet.balance * price
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

        return asset.get_presentation_amount(-loan.balance)

    def get_equity(self, asset: Asset):
        wallet = self.get_wallet(asset)
        loan = self.get_loan_wallet(asset)

        if wallet:
            wallet_value = wallet.balance
        else:
            wallet_value = 0

        if loan:
            loan_value = loan.balance
        else:
            loan_value = 0

        return asset.get_presentation_amount(loan_value + wallet_value)

    class Meta:
        model = Asset
        fields = (*AssetSerializerMini.Meta.fields, 'free', 'balance', 'balance_usdt', 'borrowed', 'equity')
        ref_name = 'margin wallets'


class MarginWalletViewSet(ModelViewSet):
    serializer_class = MarginAssetListSerializer
    queryset = Asset.live_objects.filter(margin_enable=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()

        account = self.request.user.account
        wallets = Wallet.objects.filter(account=account, market=Wallet.MARGIN, variant__isnull=True)
        loans = Wallet.objects.filter(account=account, market=Wallet.LOAN)

        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}
        ctx['asset_to_loan'] = {wallet.asset_id: wallet for wallet in loans}

        return ctx
