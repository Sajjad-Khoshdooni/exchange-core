import logging
from decimal import Decimal

from django.db.models import Q
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ledger.models import Wallet
from ledger.models.asset import Asset
from ledger.models.wallet import ReserveWallet
from ledger.utils.external_price import SELL
from ledger.utils.precision import get_presentation_amount, floor_precision
from ledger.utils.price import get_prices, get_coins_symbols

logger = logging.getLogger(__name__)


class WalletsOverviewAPIView(APIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def aggregate_wallets_values(wallets, prices):
        total_irt_value = total_usdt_value = Decimal(0)
        for wallet in wallets:
            coin = wallet.asset.symbol
            price_usdt = prices.get(coin + Asset.USDT, 0)
            price_irt = prices.get(coin + Asset.IRT, 0)

            total_usdt_value += wallet.balance * price_usdt
            total_irt_value += wallet.balance * price_irt
        return {
            'IRT': get_presentation_amount(floor_precision(total_irt_value)),
            'USDT': get_presentation_amount(floor_precision(total_usdt_value))
        }

    def get(self, request: Request):
        account = request.user.get_account()
        disabled_assets = Wallet.objects.filter(
            account=account,
            asset__enable=False
        ).exclude(balance=0).values_list('asset_id', flat=True)

        coins = list(Asset.objects.filter(Q(enable=True) | Q(id__in=disabled_assets)).values_list('symbol', flat=True))
        prices = get_prices(get_coins_symbols(coins), side=SELL, allow_stale=True)

        spot_wallets = Wallet.objects.filter(
            account=account, market=Wallet.SPOT, variant__isnull=True
        ).exclude(balance=0)

        reserved_variants = ReserveWallet.objects.filter(sender__account=account).values_list('group_id', flat=True)
        strategy_wallets = Wallet.objects.filter(
            account=account, market__in=(Wallet.SPOT, Wallet.MARGIN), variant__isnull=False,
            variant__in=reserved_variants
        ).exclude(balance=0)

        stake_wallets = Wallet.objects.filter(account=account, market=Wallet.STAKE).exclude(balance=0)

        return Response({
            Wallet.SPOT: self.aggregate_wallets_values(spot_wallets, prices),
            'strategy': self.aggregate_wallets_values(strategy_wallets, prices),
            Wallet.STAKE: self.aggregate_wallets_values(stake_wallets, prices),
        })
