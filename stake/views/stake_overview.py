import logging
from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ledger.models import Wallet
from ledger.models.asset import Asset
from ledger.utils.precision import get_presentation_amount, floor_precision
from stake.models import StakeRevenue

logger = logging.getLogger(__name__)


class StakeOverviewAPIView(APIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def aggregate_revenue_values(asset_revenues, external_prices, market_prices, tether_irt):
        total_irt_value = total_usdt_value = Decimal(0)
        for asset_revenue in asset_revenues:
            price_usdt = market_prices['USDT'].get(asset_revenue['symbol'], 0) or \
                         external_prices.get(asset_revenue['symbol'], 0)
            price_irt = market_prices['IRT'].get(asset_revenue['symbol'], 0) or \
                        external_prices.get(asset_revenue['symbol'], 0) * tether_irt

            total_usdt_value += asset_revenue['revenue'] * price_usdt
            total_irt_value += asset_revenue['revenue'] * price_irt
        return {
            'IRT': get_presentation_amount(floor_precision(total_irt_value)),
            'USDT': get_presentation_amount(floor_precision(total_usdt_value))
        }

    def get(self, request: Request):
        account = request.user.get_account()

        stake_wallets = Wallet.objects.filter(account=account, market=Wallet.STAKE).exclude(balance=0)
        coins = stake_wallets.values_list('asset__symbol', flat=True)
        prices, market_prices, tether_irt = Asset.get_current_prices(coins)

        assets_total_revenues = StakeRevenue.objects.filter(
            stake_request__account=account
        ).values('stake_request__stake_option__asset__symbol').annotate(
            symbol=F('stake_request__stake_option__asset__symbol'),
            total_revenue=Sum('revenue'),
        )

        assets_last_revenues = StakeRevenue.objects.filter(
            created=timezone.now().astimezone().date(),
            stake_request__account=account
        ).values('stake_request__stake_option__asset__symbol', 'created').annotate(
            symbol=F('stake_request__stake_option__asset__symbol'),
            total_revenue=Sum('revenue'),
        )

        from ledger.views import WalletsOverviewAPIView
        return Response({
            'total': WalletsOverviewAPIView.aggregate_wallets_values(
                stake_wallets, prices, market_prices, tether_irt
            ),
            'total_revenue': self.aggregate_revenue_values(assets_total_revenues, prices, market_prices, tether_irt),
            'last_revenue': self.aggregate_revenue_values(assets_last_revenues, prices, market_prices, tether_irt),
        })
