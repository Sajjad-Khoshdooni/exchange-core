import math

from ledger.models import Asset
from ledger.utils.price import get_tether_irt_price, BUY, get_prices_dict


def fix_quantity_steps():
    symbols = list(Asset.objects.filter(enable=True).values_list('symbol', flat=True))
    prices = get_prices_dict(coins=symbols, side=BUY, allow_stale=True)
    tether = get_tether_irt_price(BUY, allow_stale=True)

    assets = Asset.objects.filter(enable=True)
    coin_to_asset = {
        a.symbol: a for a in assets
    }

    for coin, price in prices.items():
        if not price:
            print(coin, 'null price')
            continue
        price_irt = price * tether
        if not price_irt:
            print(coin, 'is zero price')
            continue
        precision = math.ceil(math.log10(price * tether))
        precision = max(0, min(precision, 8))
        step = 10 ** -precision
        asset = coin_to_asset[coin]
        asset.trade_quantity_step = step
        asset.save(update_fields=['trade_quantity_step'])
