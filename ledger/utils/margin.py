from decimal import Decimal
from typing import Tuple

from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.price import get_price, SELL, BUY


def get_promissory_and_total_assets_usdt(account: Account) -> Tuple[Decimal, Decimal]:
    wallets = Wallet.objects.filter(account=account, market=Wallet.MARGIN)

    promissory, total = Decimal('0'), Decimal('0')

    for wallet in wallets:
        balance = wallet.get_balance()
        if balance >= 0:
            total += balance * get_price(wallet.asset.symbol, BUY)
        else:
            promissory += balance * get_price(wallet.asset.symbol, SELL)

    return -promissory, total


def get_margin_level(account: Account):
    promissory, total_assets = get_promissory_and_total_assets_usdt(account)

    if promissory == 0:
        return Decimal('inf')
    else:
        return total_assets / promissory
