import logging
from collections import defaultdict
from decimal import Decimal

from django.db import models
from django.db.models import F, Sum, Case, When, Value as V

from accounts.models import Account
from ledger.models import Wallet, Asset, Trx
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_trading_price_usdt, BUY


logger = logging.getLogger(__name__)


class PNLHistory(models.Model):
    date = models.DateField()
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)
    market = models.CharField(
        max_length=8,
        default=Wallet.SPOT,
        choices=((Wallet.SPOT, Wallet.SPOT), (Wallet.MARGIN, Wallet.MARGIN)),
    )
    base_asset = models.CharField(
        max_length=8,
        choices=((Asset.IRT, Asset.IRT), (Asset.USDT, Asset.USDT))
    )

    snapshot_balance = get_amount_field(default=Decimal(0))
    profit = get_amount_field(default=Decimal(0), validators=())

    class Meta:
        unique_together = [('date', 'account', 'market', 'base_asset')]

    @staticmethod
    def calculate_amounts_in_usdt(account_wallets: dict, account_input_outputs: dict, last_snapshot_balance: Decimal,
                                  usdt_price: Decimal):
        def get_price(coin: str):
            if coin == Asset.USDT:
                return 1
            elif coin == Asset.IRT:
                return 1 / usdt_price
            return get_trading_price_usdt(coin, BUY, raw_price=True)

        missing_price_coins = list(filter(
            lambda coin: not get_price(coin),
            set(account_wallets.keys()).union(set(account_input_outputs.keys())))
        )
        if missing_price_coins:
            raise Exception(f'Missing coin prices for {missing_price_coins}')

        snapshot_balance = sum(map(
            lambda coin_amount: Decimal(get_price(coin_amount[0])) * coin_amount[1], account_wallets.items()
        ))
        input_output_amount = sum(map(
            lambda coin_amount: Decimal(get_price(coin_amount[0])) * coin_amount[1], account_input_outputs.items()
        ))
        profit = snapshot_balance - last_snapshot_balance - input_output_amount
        return snapshot_balance, profit, input_output_amount

    @staticmethod
    def get_for_account_market(account, market, all_items):
        return {
            coin: balance for (w_market, w_account, coin), balance in all_items
            if account == w_account and market == w_market
        }

    @staticmethod
    def get_all_wallets():
        return {
            (wallet['wallet_market'], wallet['account'], wallet['asset__symbol']): wallet['total_balance'] for
            wallet in Wallet.objects.filter(
                account__type=Account.ORDINARY,
                asset__enable=True,
            ).exclude(balance=0).annotate(
                wallet_market=Case(When(market=Wallet.LOAN, then=V(Wallet.MARGIN)), default='market')
            ).values('wallet_market', 'account', 'asset__symbol').annotate(total_balance=Sum('balance')).values(
                'wallet_market', 'account', 'asset__symbol', 'total_balance'
            )
        }

    @staticmethod
    def get_all_in_out(start=None, end=None):
        datetime_filter = {'created__range': (start, end)} if start else {}
        in_out_dict = defaultdict(Decimal)
        in_out_trxs = Trx.objects.filter(
            **datetime_filter
        ).exclude(
            scope__in=(Trx.TRADE, Trx.COMMISSION, Trx.PRIZE, Trx.STAKE_REVENUE, Trx.STAKE)
        ).annotate(asset=F('sender__asset__symbol')).values(
            'sender__market', 'receiver__market', 'asset', 'sender__account', 'receiver__account'
        ).annotate(total_amount=Sum('amount'))

        for trx in in_out_trxs:
            in_out_dict[(trx['sender__market'], trx['sender__account'], trx['asset'])] -= trx['total_amount']
            in_out_dict[(trx['receiver__market'], trx['receiver__account'], trx['asset'])] += trx['total_amount']
        return in_out_dict

    @classmethod
    def get_last_histories(cls):
        return {
            (pnl['account'], pnl['market'], pnl['base_asset']): pnl['snapshot_balance'] for pnl in
            cls.objects.order_by('account', 'market', 'base_asset', '-date').distinct(
                'account', 'market', 'base_asset'
            ).values('account', 'market', 'base_asset', 'snapshot_balance')
        }
