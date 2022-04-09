import logging
from decimal import Decimal

from accounts.models import Account
from ledger.models import Wallet, Trx, OTCTrade, OTCRequest, Asset
from ledger.models.margin import MarginLiquidation
from ledger.utils.margin import MarginInfo
from ledger.utils.price import get_trading_price_usdt, SELL, BUY
from provider.utils import round_with_step_size

logger = logging.getLogger(__name__)


def get_wallet_balances(account: Account, market: str):
    wallets = Wallet.objects.filter(account=account, market=market)

    balances = {}

    for wallet in wallets:
        free = wallet.get_free()
        if free != 0:
            balances[wallet] = free

    return balances


class LiquidationEngine:

    def __init__(self, margin_liquidation: MarginLiquidation, margin_info: MarginInfo):
        self.account = margin_liquidation.account
        self.margin_info = margin_info
        self.margin_liquidation = margin_liquidation

        self.liquidation_amount = self.margin_info.get_liquidation_amount()

        self.tether = Asset.get(Asset.USDT)

        if self.finished:
            self.info_log('Skipping liquidation...')
            return

        self.margin_wallets = get_wallet_balances(self.account, Wallet.MARGIN)
        self.borrowed_wallets = {
            wallet: -amount for (wallet, amount) in get_wallet_balances(self.account, Wallet.LOAN).items()
        }

    def info_log(self, msg):
        logger.info(msg + ' (id=%s)' % self.margin_liquidation.id)

    def start(self):
        self.info_log('Starting liquidation (liquidation_amount=%s$)' % self.liquidation_amount)

        self._fast_liquidate()

        self.info_log('After fast_liquidation (liquidation_amount=%s$)' % self.liquidation_amount)

        if not self.finished:
            self._provide_tether()
            self.info_log('After providing_tether (liquidation_amount=%s$)' % self.liquidation_amount)

            self._liquidate_funds()

            self.info_log('After liquidate_funds (liquidation_amount=%s$)' % self.liquidation_amount)

        self.info_log('Liquidation completed')

    def _fast_liquidate(self):
        margin_asset_to_wallet = {w.asset: w for w in self.margin_wallets}
        borrowed_asset_to_wallet = {w.asset: w for w in self.borrowed_wallets}

        shared_assets = set(margin_asset_to_wallet) & set(borrowed_asset_to_wallet)

        if shared_assets:
            self.info_log('Using fast liquidation')

            for asset in shared_assets:

                if self.finished:
                    return

                borrowed_wallet = borrowed_asset_to_wallet[asset]
                borrowed_amount = self.borrowed_wallets[borrowed_wallet]

                margin_wallet = margin_asset_to_wallet[asset]
                margin_amount = self.margin_wallets[margin_wallet]

                price = get_trading_price_usdt(asset.symbol, BUY)
                max_amount = self.liquidation_amount / price

                amount = min(margin_amount, borrowed_amount, max_amount)

                self.info_log(
                    'Fast liquidating %s %s (margin_amount=%s, borrowed_amount=%s, liquid_amount=%s, price=%s, max_amount=%s)' % (
                        amount, asset, margin_amount, borrowed_amount, self.liquidation_amount, price, max_amount
                    )
                )

                Trx.transaction(
                    sender=margin_asset_to_wallet[asset],
                    receiver=borrowed_asset_to_wallet[asset],
                    amount=amount,
                    scope=Trx.FAST_LIQUID,
                    group_id=self.margin_liquidation.group_id
                )

                self.liquidation_amount -= amount * price

                self.borrowed_wallets[borrowed_wallet] -= amount
                self.margin_wallets[margin_wallet] -= amount

    def _provide_tether(self):

        margin_wallet_values = {
            wallet: balance * get_trading_price_usdt(wallet.asset.symbol, BUY) for (wallet, balance) in
            self.margin_wallets.items()
        }

        margin_wallets = list(self.margin_wallets.keys())
        margin_wallets.sort(key=lambda w: margin_wallet_values.get(w, 0), reverse=True)

        margin_tether_wallet = self.tether.get_wallet(self.account, Wallet.MARGIN)
        tether_amount = margin_tether_wallet.get_free()

        to_provide_tether = self.liquidation_amount - tether_amount

        self.info_log('providing tether %s$' % to_provide_tether)

        for wallet in margin_wallets:
            if to_provide_tether < 0.1:
                return

            if wallet.asset.symbol == Asset.USDT:
                continue

            self.info_log('providing tether with %s' % wallet.asset)

            value = margin_wallet_values[wallet]

            max_value = min(to_provide_tether * Decimal('1.05'), value)
            amount = max_value / value * self.margin_wallets[wallet]
            amount = round_with_step_size(amount, wallet.asset.trade_quantity_step)

            if amount < wallet.asset.min_trade_quantity:
                continue

            request = OTCRequest.new_trade(
                self.account,
                market=Wallet.MARGIN,
                from_asset=wallet.asset,
                to_asset=self.tether,
                from_amount=amount,
                allow_small_trades=True
            )

            OTCTrade.execute_trade(request)

            to_provide_tether -= request.to_amount

    def _liquidate_funds(self):
        self.info_log('liquidating funds')

        borrowed_wallet_values = {
            wallet: balance * get_trading_price_usdt(wallet.asset.symbol, BUY) for (wallet, balance) in
            self.borrowed_wallets.items()
        }

        borrowed_wallets = list(self.borrowed_wallets.keys())
        borrowed_wallets.sort(key=lambda w: borrowed_wallet_values.get(w, 0), reverse=True)

        margin_tether_wallet = self.tether.get_wallet(self.account, Wallet.MARGIN)
        tether_amount = margin_tether_wallet.get_free()

        for wallet in borrowed_wallets:

            if self.liquidation_amount < 0.1 or tether_amount < 0.1:
                return

            value = borrowed_wallet_values[wallet]

            max_value = min(self.liquidation_amount * Decimal('1.002'), value, tether_amount / Decimal('1.01'))
            amount = max_value / value * self.borrowed_wallets[wallet]
            amount = round_with_step_size(amount, wallet.asset.trade_quantity_step)

            if amount < wallet.asset.min_trade_quantity:
                continue

            if wallet.asset.symbol == Asset.USDT:
                transfer_amount = amount
            else:
                request = OTCRequest.new_trade(
                    self.account,
                    market=Wallet.MARGIN,
                    from_asset=self.tether,
                    to_asset=wallet.asset,
                    to_amount=amount,
                    allow_small_trades=True
                )

                OTCTrade.execute_trade(request)

                transfer_amount = request.to_amount

            Trx.transaction(
                sender=wallet.asset.get_wallet(self.account, market=Wallet.MARGIN),
                receiver=wallet,
                amount=transfer_amount,
                scope=Trx.LIQUID,
                group_id=self.margin_liquidation.group_id,
            )

            tether_amount = margin_tether_wallet.get_balance()
            self.liquidation_amount -= amount

    @property
    def finished(self):
        return self.liquidation_amount < 0.1
