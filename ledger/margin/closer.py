import logging
from decimal import Decimal

from yekta_config.config import config

from ledger.models import Wallet, OTCTrade, OTCRequest, Asset, CloseRequest, MarginLoan, Trx
from ledger.utils.fields import PENDING, DONE
from ledger.utils.price import get_trading_price_usdt, SELL
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)

MARGIN_INSURANCE_ACCOUNT = config('MARGIN_INSURANCE_ACCOUNT', cast=int)

LIQUIDATION_FEE_RATE = Decimal('0.05')


class MarginCloser:
    def __init__(self, close_request: CloseRequest, force_liquidation: bool):
        assert close_request.status == PENDING

        self.account = close_request.account
        self.request = close_request

        self.tether = Asset.get(Asset.USDT)
        self.force_liquidation = force_liquidation

        self._liquidated_value = 0

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

        if not self.is_done():
            self.info_log('providing tether')
            self._provide_tether()

            self.info_log('providing tether')
            self._liquidate_funds()

        self.info_log('acquiring liquidation fee')
        self._acquire_liquidation_fee()

        if self.is_done():
            self.info_log('finishing margin closing.')
            self.set_finished()
            return
        else:
            raise Exception('Margin account is not closed even after liquidating funds')

    def _acquire_liquidation_fee(self):
        fee = self._liquidated_value * LIQUIDATION_FEE_RATE
        margin_usdt_wallet = self.tether.get_wallet(self.account, market=Wallet.MARGIN)
        margin_insurance_usdt_wallet = self.tether.get_wallet(MARGIN_INSURANCE_ACCOUNT)

        with WalletPipeline() as pipeline:
            pipeline.new_trx(
                sender=margin_usdt_wallet,
                receiver=margin_insurance_usdt_wallet,
                amount=min(fee, margin_usdt_wallet.balance),
                scope=Trx.TRANSFER,
                group_id=self.request.group_id
            )

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

            asset = margin_wallet.asset

            # todo: add reason field to margin loan
            MarginLoan.new_loan(
                account=self.account,
                asset=margin_wallet.asset,
                amount=amount,
                loan_type=MarginLoan.REPAY
            )

            price = get_trading_price_usdt(asset.symbol, side=SELL, raw_price=True)
            self._liquidated_value += amount * price

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

        requests = []
        usdt_need = 0

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
                    allow_small_trades=True,
                    check_enough_balance=False
                )

                requests.append(request)

                usdt_need += request.from_amount

        margin_usdt_wallet = self.tether.get_wallet(self.account, market=Wallet.MARGIN)

        if usdt_need > margin_usdt_wallet.balance:
            insure = usdt_need - margin_usdt_wallet.balance
            self.info_log('Asking insurance to give funds %s$' % insure)

            margin_insurance_usdt_wallet = self.tether.get_wallet(MARGIN_INSURANCE_ACCOUNT)

            with WalletPipeline() as pipeline:
                pipeline.new_trx(
                    sender=margin_insurance_usdt_wallet,
                    receiver=margin_usdt_wallet,
                    amount=insure,
                    scope=Trx.TRANSFER,
                    group_id=self.request.group_id
                )

        for request in requests:
            OTCTrade.execute_trade(request)

        for wallet in loan_wallets:
            asset = wallet.asset
            amount = -wallet.balance

            MarginLoan.new_loan(
                account=self.account,
                asset=asset,
                amount=amount,
                loan_type=MarginLoan.REPAY
            )

            price = get_trading_price_usdt(asset.symbol, side=SELL, raw_price=True)
            self._liquidated_value += amount * price

    def is_done(self):
        return not self._get_loan_wallets().exists()

    def set_finished(self):
        self.request.status = DONE
        self.request.save()

    def cancel_open_orders(self):
        from market.models import Order
        Order.cancel_orders(Order.open_objects.filter(wallet__account=self.account))
