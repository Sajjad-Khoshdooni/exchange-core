from decimal import Decimal

from django.db.models import Sum

from accounts.models import Account
from ledger.models import Asset, Network, Wallet
from ledger.utils.price import SELL

TRADE, BORROW, LIQUIDATION, WITHDRAW, HEDGE, PROVIDE_BASE, FAKE = \
    'trade', 'borrow', 'liquid', 'withdraw', 'hedge', 'prv-base', 'fake'


def get_hedge(cls, asset: Asset):
    """
    how much assets we have more!

    out = -internal - binance transfer deposit
    hedge = all assets - users = (internal + binance manual deposit + binance transfer deposit + binance trades)
            + system + out = system + binance trades + binance manual deposit

    given binance manual deposit = 0 -> hedge = system + binance manual deposit + binance trades
    """

    system_balance = Wallet.objects.filter(
        account__type=Account.SYSTEM,
        asset=asset
    ).aggregate(
        sum=Sum('balance')
    )['sum'] or 0

    orders = get_total_orders_amount_sum(asset)

    orders_amount = 0

    for order in orders:
        amount = order['amount']

        if order['side'] == SELL:
            amount = -amount

        orders_amount += amount

    return system_balance + orders_amount


def get_total_orders_amount_sum(asset: Asset) -> list:
    pass


def new_provider_order(asset: Asset, scope: str, amount: Decimal, side: str):
    pass


def hedge_asset(asset: Asset):
    pass


def new_provider_withdraw(asset: Asset, network: Network, transfer_amount: Decimal, withdraw_fee: Decimal, address: str,
                     caller_id: str = '', memo: str = None):
    pass


def new_hedged_spot_buy(asset: Asset, amount: Decimal, spot_side: str, caller_id: str):
    pass


def get_provider_transfer_status(requester_id: int):
    pass
