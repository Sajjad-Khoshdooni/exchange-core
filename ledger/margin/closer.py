import logging
from decimal import Decimal

from accounts.models import Account
from ledger.models import Wallet, Trx, OTCTrade, OTCRequest, Asset, CloseRequest, MarginLoan
from ledger.utils.price import get_trading_price_usdt, BUY
from ledger.utils.wallet_pipeline import WalletPipeline
from provider.utils import round_with_step_size

logger = logging.getLogger(__name__)



class MarginCloser:
    def __init__(self, close_request: CloseRequest):
        assert close_request.status == CloseRequest.NEW

        self.account = close_request.account
        self.request = close_request

        self.tether = Asset.get(Asset.USDT)

    def info_log(self, msg):
        logger.info(msg + ' (id=%s)' % self.request.id)

    def _get_margin_wallets(self):
        return Wallet.objects.filter(account=self.account, market=Wallet.MARGIN, balance__gt=0)

    def _get_loan_wallets(self):
        return Wallet.objects.filter(account=self.account, market=Wallet.LOAN, balance__lt=0)

    def start(self):
        self.info_log('Starting closing margin positions')

        if self.is_done():
            self.info_log('finishing margin closing. [no action taken]')
            self.set_finished()
            return

        self.info_log('canceling open orders')
        self.cancel_open_orders()

        self.info_log('fast repay')
        self._fast_repay()

        if self.is_done():
            self.info_log('finishing margin closing.')
            self.set_finished()
            return

        self.info_log('providing tether')
        self._provide_tether()

        self.info_log('providing tether')
        self._liquidate_funds()

        if self.is_done():
            self.info_log('finishing margin closing.')
            self.set_finished()
            return
        else:
            raise Exception('')

    def _fast_repay(self):
        margin_wallets = self._get_margin_wallets()
        loan_wallets = self._get_loan_wallets()

        margin_asset_to_wallet = {w.asset_id: w for w in margin_wallets}
        loan_asset_to_wallet = {w.asset_id: w for w in loan_wallets}

        shared_assets = set(margin_asset_to_wallet) & set(loan_asset_to_wallet)

        if not shared_assets:
            self.info_log('no fast repay candidate')
            return

        for asset_id in shared_assets:
            loan_wallet = loan_wallets[asset_id]
            margin_wallet = margin_wallets[asset_id]

            amount = min(margin_wallet.balance, -loan_wallet.balance)

            MarginLoan.new_loan(
                account=self.account,
                asset=margin_wallet.asset,
                amount=amount,
                loan_type=MarginLoan.REPAY
            )

    def _provide_tether(self):

        # todo: Only provider as much as we need to repay

        margin_asset_to_wallet = {w.asset_id: w for w in margin_wallets}
        loan_asset_to_wallet = {w.asset_id: w for w in loan_wallets}


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

    def _liquidate_funds(self):
        self.info_log('liquidating funds')

        borrowed_wallet_values = {
            wallet: balance * get_trading_price_usdt(wallet.asset.symbol, BUY) for (wallet, balance) in
            self.loan_wallets.items()
        }

        borrowed_wallets = list(self.loan_wallets.keys())
        borrowed_wallets.sort(key=lambda w: borrowed_wallet_values.get(w, 0), reverse=True)

        margin_tether_wallet = self.tether.get_wallet(self.account, Wallet.MARGIN)
        tether_amount = margin_tether_wallet.get_free()

        for wallet in borrowed_wallets:
            borrowed_value = borrowed_wallet_values[wallet]

            to_buy_value = min(borrowed_value, tether_amount)

            if wallet.asset.symbol == Asset.USDT:
                transfer_amount = to_buy_value
            else:
                request = OTCRequest.new_trade(
                    self.account,
                    market=Wallet.MARGIN,
                    from_asset=self.tether,
                    to_asset=wallet.asset,
                    from_amount=to_buy_value,
                    allow_small_trades=True
                )

                OTCTrade.execute_trade(request)

                transfer_amount = request.to_amount

            sender = wallet.asset.get_wallet(self.account, market=Wallet.MARGIN)

            with WalletPipeline() as pipeline:
                pipeline.new_trx(
                    sender=sender,
                    receiver=wallet,
                    amount=min(transfer_amount, sender.balance),
                    scope=Trx.LIQUID,
                    group_id=self.request.group_id,
                )

            tether_amount = margin_tether_wallet.get_balance()
            self.liquidation_amount -= to_buy_value

    def is_done(self):
        return not self._get_loan_wallets().exists()

    def set_finished(self):
        self.request.status = CloseRequest.DONE
        self.request.save()

    def cancel_open_orders(self):
        from market.models import Order
        Order.cancel_orders(Order.open_objects.filter(wallet__account=self.account))
