import logging
from decimal import Decimal

from accounts.models import Account
from ledger.models import Wallet, Trx, OTCTrade, OTCRequest, Asset
from ledger.models.margin import CloseRequest
from ledger.margin.margin_info import MarginInfo
from ledger.utils.price import get_trading_price_usdt, BUY
from provider.utils import round_with_step_size


logger = logging.getLogger(__name__)


INF = Decimal('INF')


def get_wallet_balances(account: Account, market: str):
    wallets = Wallet.objects.filter(account=account, market=market)

    balances = {}

    for wallet in wallets:
        free = wallet.get_free()
        if free != 0:
            balances[wallet] = free

    return balances


class PositionCloser:

    def __init__(self, close_request: CloseRequest, close_value: Decimal = INF):
        self.account = close_request.account
        self.close_request = close_request

        self.to_close_value = close_value

        self.tether = Asset.get(Asset.USDT)

        if self.finished:
            self.info_log('Skipping closing...')
            return

        self.margin_wallets = get_wallet_balances(self.account, Wallet.MARGIN)
        self.borrowed_wallets = {
            wallet: -amount for (wallet, amount) in get_wallet_balances(self.account, Wallet.LOAN).items()
        }

    def info_log(self, msg):
        logger.info(msg + ' (id=%s)' % self.close_request.id)

    def start(self):
        self.info_log('Starting closing (close_amount=%s$)' % self.to_close_value)

        self._fast_closing()

        self.info_log('After fast_liquidation (liquidation_amount=%s$)' % self.to_close_value)

        if not self.finished:
            self._provide_tether()
            self.info_log('After providing_tether (liquidation_amount=%s$)' % self.to_close_value)

            self._close_funds()

            self.info_log('After liquidate_funds (liquidation_amount=%s$)' % self.to_close_value)

        self.info_log('Liquidation completed')

    # def _force_release_margin_locks(self):
    #     locked_wallets = Wallet.objects.filter(account=self.account, locked__gt=0)
    #
    #     for wallet in locked_wallets:
    #         wallet.

    def _fast_closing(self):
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

                if self.to_close_value is INF:
                    price = 0
                    max_amount = INF
                else:
                    price = get_trading_price_usdt(asset.symbol, BUY)
                    max_amount = self.to_close_value / price

                amount = min(margin_amount, borrowed_amount, max_amount)

                self.info_log(
                    'Fast liquidating %s %s (margin_amount=%s, borrowed_amount=%s, liquid_amount=%s)' % (
                        amount, asset, margin_amount, borrowed_amount, self.to_close_value
                    )
                )

                Trx.transaction(
                    sender=margin_asset_to_wallet[asset],
                    receiver=borrowed_asset_to_wallet[asset],
                    amount=amount,
                    scope=Trx.FAST_LIQUID,
                    group_id=self.close_request.group_id
                )

                self.to_close_value -= amount * price

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

        to_provide_tether = self.to_close_value - tether_amount

        self.info_log('providing tether %s$' % to_provide_tether)

        for wallet in margin_wallets:
            if to_provide_tether < 0.1:
                return

            if wallet.asset.symbol == Asset.USDT:
                continue

            self.info_log('providing tether with %s' % wallet.asset)

            value = margin_wallet_values[wallet]

            if value < Decimal('0.1'):
                continue

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

    def _close_funds(self):
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

            if self.to_close_value < 0.1 or tether_amount < 0.1:
                return

            value = borrowed_wallet_values[wallet]

            max_value = min(self.to_close_value * Decimal('1.002'), value, tether_amount / Decimal('1.01'))
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

            sender = wallet.asset.get_wallet(self.account, market=Wallet.MARGIN)

            Trx.transaction(
                sender=sender,
                receiver=wallet,
                amount=min(transfer_amount, sender.balance),
                scope=Trx.LIQUID,
                group_id=self.close_request.group_id,
            )

            tether_amount = margin_tether_wallet.get_balance()
            self.to_close_value -= amount

    @property
    def finished(self):
        return self.to_close_value <= 0 or not self.account.has_debt()
