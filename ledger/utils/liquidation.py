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
            logger.info('Skipping liquidation...')
            return

        self.margin_wallets = get_wallet_balances(account, Wallet.MARGIN)
        self.borrowed_wallets = {wallet: -amount for (wallet, amount) in get_wallet_balances(account, Wallet.LOAN).items()}

    def start(self):
        logger.info('Starting liquidation for %s' % self.account.id)

        self._fast_liquidate()

        if not self.finished:
            self._provide_tether()
            self._liquidate_funds()

        logger.info('Liquidation completed')

    def _fast_liquidate(self):
        margin_asset_to_wallet = {w.asset: w for w in self.margin_wallets}
        borrowed_asset_to_wallet = {w.asset: w for w in self.borrowed_wallets}

        shared_assets = set(margin_asset_to_wallet) & set(borrowed_asset_to_wallet)

        if shared_assets:
            logger.info('Using fast liquidation')

            for asset in shared_assets:

                if self.finished:
                    return

                borrowed_wallet = borrowed_asset_to_wallet[asset]
                borrowed_amount = self.borrowed_wallets[borrowed_wallet]

                margin_wallet = margin_asset_to_wallet[asset]
                margin_amount = self.margin_wallets[margin_wallet]

                price = get_trading_price_usdt(asset.symbol, SELL)
                max_amount = self.liquidation_amount / price

                amount = min(margin_amount, borrowed_amount, max_amount)

                logger.info('Fast liquidating %s %s' % (amount, asset))

                Trx.transaction(
                    sender=margin_asset_to_wallet[asset],
                    receiver=borrowed_asset_to_wallet[asset],
                    amount=amount,
                    scope=Trx.LIQUID,
                    group_id=self.margin_liquidation.group_id
                )

                self.liquidation_amount -= amount * price

                self.borrowed_wallets[borrowed_wallet] -= amount
                self.margin_wallets[margin_wallet] -= amount

    def _provide_tether(self):
        logger.info('providing tether')

        margin_wallet_values = {
            wallet: balance * get_trading_price_usdt(wallet.asset.symbol, SELL) for (wallet, balance) in
            self.margin_wallets.items()
        }

        margin_wallets = list(self.margin_wallets.keys())
        margin_wallets.sort(key=lambda w: margin_wallet_values.get(w, 0), reverse=True)

        margin_tether_wallet = self.tether.get_wallet(self.account, Wallet.MARGIN)
        tether_amount = margin_tether_wallet.get_free()

        to_provide_tether = self.liquidation_amount - tether_amount

        for wallet in margin_wallets:
            if wallet.asset.symbol == Asset.USDT:
                continue

            if to_provide_tether < 0.1:
                return

            logger.info('providing tether with %s' % wallet.asset)

            value = margin_wallet_values[wallet]

            max_value = min(to_provide_tether * Decimal('1.01'), value)
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
        logger.info('liquidating funds')

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

            request = OTCRequest.new_trade(
                self.account,
                market=Wallet.MARGIN,
                from_asset=self.tether,
                to_asset=wallet.asset,
                to_amount=amount,
                allow_small_trades=True
            )

            OTCTrade.execute_trade(request)

            Trx.transaction(
                sender=wallet.asset.get_wallet(self.account, market=Wallet.MARGIN),
                receiver=wallet,
                amount=amount,
                scope=Trx.LIQUID,
                group_id=self.margin_liquidation.group_id,
            )

            tether_amount = margin_tether_wallet.get_balance()
            self.liquidation_amount -= amount

    @property
    def finished(self):
        return self.liquidation_amount < 0.1
