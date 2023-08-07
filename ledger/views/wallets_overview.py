import logging
from decimal import Decimal

from django.db.models import Min, Q
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ledger.models import Wallet
from ledger.models.asset import Asset
from ledger.models.wallet import ReserveWallet
from ledger.utils.external_price import get_external_price, get_external_usdt_prices, BUY, SELL
from ledger.utils.precision import get_presentation_amount, floor_precision
from market.models import Order

logger = logging.getLogger(__name__)


class WalletsOverviewAPIView(APIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def aggregate_wallets_values(wallets, external_prices, market_prices, tether_irt):
        total_irt_value = total_usdt_value = Decimal(0)
        for wallet in wallets:
            price_usdt = market_prices['USDT'].get(wallet.asset.symbol, 0) or \
                         external_prices.get(wallet.asset.symbol, 0)
            price_irt = market_prices['IRT'].get(wallet.asset.symbol, 0) or \
                        external_prices.get(wallet.asset.symbol, 0) * tether_irt

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

        prices = get_external_usdt_prices(
            coins=coins,
            side=BUY,
            apply_otc_spread=True
        )
        market_prices = {}
        for base_asset in ('IRT', 'USDT'):
            market_prices[base_asset] = {
                o['symbol__name'].replace(base_asset, ''): o['best_ask'] for o in Order.open_objects.filter(
                    side=SELL,
                    symbol__enable=True,
                    symbol__name__in=map(lambda s: f'{s}{base_asset}', coins)
                ).values('symbol__name').annotate(best_ask=Min('price'))
            }
        tether_irt = get_external_price(coin=Asset.USDT, base_coin=Asset.IRT, side=BUY, allow_stale=True)

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
            Wallet.SPOT: self.aggregate_wallets_values(spot_wallets, prices, market_prices, tether_irt),
            'strategy': self.aggregate_wallets_values(strategy_wallets, prices, market_prices, tether_irt),
            Wallet.STAKE: self.aggregate_wallets_values(stake_wallets, prices, market_prices, tether_irt),
        })
