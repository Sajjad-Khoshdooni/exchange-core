from accounts.models import User
from ledger.models import Wallet, Asset
from ledger.utils.external_price import get_external_price, BUY


def get_holders(coin: str, min_irt_vale: int = 10000):
    price = get_external_price(coin, Asset.IRT, BUY)
    min_amount = min_irt_vale / price
    wallets = Wallet.objects.filter(asset__symbol=coin, balance__gte=min_amount)
    user_ids = set(wallets.values_list('account__user_id', flat=True))
    return User.objects.filter(id__in=user_ids)


def print_holders(coin, min_irt_value: int = 10000):
    print('\n'.join(list(get_holders(coin, min_irt_value).values_list('phone', flat=True))))
