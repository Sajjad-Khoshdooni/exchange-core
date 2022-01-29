from accounts.models import Account
from decimal import Decimal

from celery import shared_task

from accounts.models import Account
from ledger.models import Wallet, Trx, OTCTrade, OTCRequest, Asset
from ledger.utils.margin import MARGIN_CALL_ML_THRESHOLD, LIQUIDATION_ML_THRESHOLD
from ledger.utils.margin import MarginInfo
import logging

from ledger.utils.price import get_trading_price_usdt, SELL, BUY
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


def get_asset_balances(account: Account, market: str):
    wallets = Wallet.objects.filter(account=account, market=market)

    balances = {}

    for wallet in wallets:
        free = wallet.get_free()
        if free != 0:
            balances[wallet.asset] = free

    return balances


class LiquidationEngine:

    def __init__(self, account: Account, margin_info: MarginInfo):
        self.account = account
        self.margin_info = margin_info

        self.liquidation_amount = self.margin_info.get_liquidation_amount()

        self.tether = Asset.get(Asset.USDT)

        if self.finished:
            logger.info('Skipping liquidation...')
            return

        self.margin_wallets = get_asset_balances(account, Wallet.MARGIN)
        self.borrowed_wallets = get_asset_balances(account, Wallet.LOAN)

        self.margin_asset_to_wallets = {
            w.asset: w for w in self.margin_wallets
        }

        self.borrowed_asset_to_wallets = {
            w.asset: w for w in self.borrowed_wallets
        }

    def start(self):
        logger.info('Starting liquidation for %s' % self.account.id)

        if not self.finished:
            self._fast_liquidate()

        if not self.finished:
            self._liquidate_funds()
            self._provide_tether()

        logger.info('Liquidation completed')

    def _fast_liquidate(self):
        shared_assets = set(self.margin_wallets) & set(self.borrowed_wallets)

        if shared_assets:
            logger.info('Using fast liquidation')

            for asset in shared_assets:

                if self.finished:
                    return

                price = get_trading_price_usdt(asset.symbol, SELL)
                max_amount = self.liquidation_amount / price
                borrowed_amount = self.borrowed_wallets[asset]
                margin_amount = self.margin_wallets[asset]

                amount = min(margin_amount, borrowed_amount, max_amount)

                logger.info('Fast liquidating %s %s' % (amount, asset))

                Trx.transaction(
                    sender=self.margin_asset_to_wallets[asset],
                    receiver=self.borrowed_asset_to_wallets[asset],
                    amount=amount,
                    scope=Trx.LIQUID
                )

                self.liquidation_amount -= amount * price

                self.borrowed_wallets[asset] -= amount
                self.margin_wallets[asset] -= amount

    def _provide_tether(self):
        margin_asset_values = {
            asset: balance * get_trading_price_usdt(asset.symbol, SELL) for (asset, balance) in
            self.margin_wallets.items()
        }

        margin_assets = list(self.margin_wallets.keys())
        margin_assets.sort(key=lambda a: margin_asset_values[a], reverse=True)

        for asset in margin_assets:
            max_value = min(self.liquidation_amount, margin_asset_values[asset])
            amount = max_value / margin_asset_values[asset] * self.margin_wallets[asset]

            request = OTCRequest.new_trade(
                self.account,
                market=Wallet.MARGIN,
                from_asset=asset,
                to_asset=self.tether,
                to_amount=amount
            )

            OTCTrade.execute_trade(request)

    def _liquidate_funds(self):
        borrowed_asset_values = {
            asset: balance * get_trading_price_usdt(asset.symbol, BUY) for (asset, balance) in self.borrowed_wallets.items()
        }

        borrowed_assets = list(self.borrowed_wallets.keys())
        borrowed_assets.sort(key=lambda a: borrowed_asset_values[a], reverse=True)

        for asset in borrowed_assets:
            max_value = min(self.liquidation_amount, borrowed_asset_values[asset])
            amount = max_value / borrowed_asset_values[asset] * self.borrowed_wallets[asset]

            request = OTCRequest.new_trade(
                self.account,
                market=Wallet.MARGIN,
                from_asset=self.tether,
                to_asset=asset,
                to_amount=amount
            )

            OTCTrade.execute_trade(request)

            Trx.transaction(
                sender=self.margin_asset_to_wallets[asset],
                receiver=self.borrowed_asset_to_wallets[asset],
                amount=amount,
                scope=Trx.LIQUID
            )

    @property
    def finished(self):
        return self.liquidation_amount < 0.01
