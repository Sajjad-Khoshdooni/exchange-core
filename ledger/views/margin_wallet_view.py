from decimal import Decimal

from django.db.models import F, Sum
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import Wallet, MarginPosition
from ledger.models.asset import Asset, AssetSerializerMini
from ledger.utils.external_price import get_external_price, BUY, SELL
from ledger.utils.precision import floor_precision, get_presentation_amount
from market.models import Order, PairSymbol


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

        account = self.request.user.get_account()
        wallets = Wallet.objects.filter(account=account, market=Wallet.MARGIN, variant__isnull=True)
        loans = Wallet.objects.filter(account=account, market=Wallet.LOAN)

        ctx['asset_to_wallet'] = {wallet.asset_id: wallet for wallet in wallets}
        ctx['asset_to_loan'] = {wallet.asset_id: wallet for wallet in loans}

        return ctx


class MarginAssetSerializer(AssetSerializerMini):
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

        return asset.get_presentation_amount(wallet['balance'])

    def get_balance_usdt(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        if asset.symbol == Asset.USDT:
            price = Decimal(1)
        else:
            symbol_id = PairSymbol.get_by(f'{asset.symbol}{Asset.USDT}').id
            # TODO: use bulk symbols prices
            price = Order.get_top_price(symbol_id, SELL) or \
                    get_external_price(coin=asset.symbol, base_coin=Asset.USDT, side=SELL, allow_stale=True)
        amount = wallet['balance'] * price
        return asset.get_presentation_price_usdt(amount)

    def get_free(self, asset: Asset):
        wallet = self.get_wallet(asset)

        if not wallet:
            return '0'

        return asset.get_presentation_amount(wallet['free'])

    def get_borrowed(self, asset: Asset):
        loan = self.get_loan_wallet(asset)

        if not loan:
            return '0'

        return asset.get_presentation_amount(-loan['balance'])

    def get_equity(self, asset: Asset):
        wallet = self.get_wallet(asset)
        loan = self.get_loan_wallet(asset)

        if wallet:
            wallet_value = wallet['balance']
        else:
            wallet_value = 0

        if loan:
            loan_value = loan['balance']
        else:
            loan_value = 0

        return asset.get_presentation_amount(loan_value + wallet_value)

    class Meta:
        model = Asset
        fields = (*AssetSerializerMini.Meta.fields, 'free', 'balance', 'balance_usdt', 'borrowed', 'equity')
        ref_name = 'margin assets'


class MarginAssetViewSet(ModelViewSet):
    serializer_class = MarginAssetSerializer
    queryset = Asset.live_objects.filter(margin_enable=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        account = self.request.user.get_account()
        wallets = Wallet.objects.filter(account=account, market=Wallet.MARGIN)
        loans = Wallet.objects.filter(account=account, market=Wallet.LOAN)
        ctx['asset_to_wallet'] = {
            asset_id: wallets.filter(asset_id=asset_id).annotate(
                balance_diff=F('balance') - F('locked')
            ).aggregate(balance=Sum('balance'), free=Sum('balance_diff')) for asset_id in
            wallets.values_list('asset_id', flat=True).distinct()
        }
        ctx['asset_to_loan'] = {
            asset_id: loans.filter(asset_id=asset_id).aggregate(balance=Sum('balance')) for asset_id in
            loans.values_list('asset_id', flat=True).distinct()
        }

        return ctx


class MarginBalanceAPIView(APIView):

    def get(self, request: Request):
        symbol_name = request.query_params.get('symbol')
        symbol = PairSymbol.objects.filter(name=symbol_name, enable=True, asset__margin_enable=True).first()
        if not symbol:
            raise ValidationError(_('{symbol} is not enable').format(symbol=symbol_name))
        side = request.query_params.get('side')
        if side == SELL:
            margin_cross_wallet = symbol.base_asset.get_wallet(request.user.account, market=Wallet.MARGIN, variant=None)
            return Response({
                'asset': symbol.base_asset.symbol,
                'free': get_presentation_amount(margin_cross_wallet.get_free() / Decimal(2))
            })

        position = MarginPosition.objects.filter(
            account=request.user.account, symbol=symbol, status=MarginPosition.OPEN).first()
        if not position or not position.amount:
            return Response({'asset': symbol.asset.symbol, 'free': get_presentation_amount(Decimal(0))})

        return Response({
            'asset': symbol.asset.symbol,
            'free': get_presentation_amount(position.amount / (Decimal(1) - symbol.taker_fee), symbol.step_size)
        })


class MarginCollateralAPIView(APIView):

    def get(self, request: Request):
        transfer_type = request.query_params.get('transfer_type')
        from ledger.models import MarginTransfer
        if transfer_type == MarginTransfer.MARGIN_TO_POSITION:
            base_asset = Asset.get(request.query_params.get('base_asset'))
            margin_cross_wallet = base_asset.get_wallet(request.user.account, market=Wallet.MARGIN, variant=None)
            return Response({
                'asset': base_asset.symbol,
                'free': get_presentation_amount(margin_cross_wallet.get_free())
            })
        elif transfer_type == MarginTransfer.POSITION_TO_MARGIN:
            symbol_name = request.query_params.get('symbol')
            symbol = PairSymbol.objects.filter(name=symbol_name, enable=True, asset__margin_enable=True).first()
            if not symbol:
                raise ValidationError(_('{symbol} is not enable').format(symbol=symbol_name))
            position = MarginPosition.objects.filter(
                account=request.user.account, symbol=symbol, status=MarginPosition.OPEN).first()
            if not position:
                return Response({'asset': symbol.asset.symbol, 'free': get_presentation_amount(Decimal(0))})

            return Response({
                'asset': symbol.base_asset.symbol,
                'free': get_presentation_amount(position.withdrawable_base_asset)
            })
