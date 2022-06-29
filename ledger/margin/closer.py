import logging

from ledger.models import Wallet, OTCTrade, OTCRequest, Asset, CloseRequest, MarginLoan

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
        return Wallet.objects.filter(account=self.account, market=Wallet.MARGIN, balance__gt=0).prefetch_related('asset')

    def _get_loan_wallets(self):
        return Wallet.objects.filter(account=self.account, market=Wallet.LOAN, balance__lt=0).prefetch_related('asset')

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
            loan_wallet = loan_asset_to_wallet[asset_id]
            margin_wallet = margin_asset_to_wallet[asset_id]

            amount = min(margin_wallet.balance, -loan_wallet.balance)

            # todo: add reason field to margin loan
            MarginLoan.new_loan(
                account=self.account,
                asset=margin_wallet.asset,
                amount=amount,
                loan_type=MarginLoan.REPAY
            )

    def _provide_tether(self):

        # todo: Only provider as much as we need to repay

        margin_wallets = self._get_margin_wallets()

        for wallet in margin_wallets:
            if not wallet.balance or wallet.asset.symbol == Asset.USDT:
                continue

            request = OTCRequest.new_trade(
                self.account,
                market=Wallet.MARGIN,
                from_asset=wallet.asset,
                to_asset=self.tether,
                from_amount=wallet.balance,
                allow_small_trades=True
            )

            OTCTrade.execute_trade(request)

    def _liquidate_funds(self):
        loan_wallets = self._get_loan_wallets()

        for wallet in loan_wallets:
            if not wallet.balance:
                continue

            if wallet.asset.symbol != Asset.USDT:
                # todo: add reason field to otc

                request = OTCRequest.new_trade(
                    self.account,
                    market=Wallet.MARGIN,
                    from_asset=self.tether,
                    to_asset=wallet.asset,
                    to_amount=-wallet.balance,
                    allow_small_trades=True
                )

                OTCTrade.execute_trade(request)

            MarginLoan.new_loan(
                account=self.account,
                asset=wallet.asset,
                amount=-wallet.balance,
                loan_type=MarginLoan.REPAY
            )

    def is_done(self):
        return not self._get_loan_wallets().exists()

    def set_finished(self):
        self.request.status = CloseRequest.DONE
        self.request.save()

    def cancel_open_orders(self):
        from market.models import Order
        Order.cancel_orders(Order.open_objects.filter(wallet__account=self.account))
