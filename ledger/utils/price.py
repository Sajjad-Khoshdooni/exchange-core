from decimal import Decimal
from typing import List, Dict, Union

from django.db.models import Min, Max

from ledger.models import Asset
from ledger.utils.cache import cache_for
from ledger.utils.external_price import fetch_external_redis_prices, BUY, SELL, get_other_side
from ledger.utils.otc import spread_to_multiplier, get_otc_spread
from market.models import Order, PairSymbol

USDT_IRT = 'USDTIRT'


def _get_external_last_prices(coins: Union[list, set], allow_stale: bool = False) -> Dict[str, Decimal]:
    prices = fetch_external_redis_prices(coins, allow_stale=allow_stale)

    last_prices = {}

    for i in range(len(prices) // 2):
        p1, p2 = prices[2 * i].price, prices[2 * i + 1].price

        if p1 and p2:
            last_price = (p1 + p2) / 2
            last_prices[prices[2 * i].coin] = last_price

    return last_prices


def get_symbol_parts(symbol: str):
    return (symbol[:-4], symbol[-4:]) if symbol.endswith('USDT') else (symbol[:-3], symbol[-3:])


@cache_for(300)
def get_all_otc_spreads(side):
    queryset = Asset.live_objects.filter(trade_enable=True)

    spreads = {}

    for asset in queryset:
        for base in (Asset.IRT, Asset.USDT):
            spreads[asset.symbol + base] = spread_to_multiplier(
                get_otc_spread(asset.symbol, side, base_coin=base), side
            )

    return spreads


def get_prices(symbols: List[str], side: str, allow_stale: bool = False) -> Dict[str, Decimal]:
    assert side in (BUY, SELL)

    if USDT_IRT not in symbols:
        symbols.append(USDT_IRT)

    if side == BUY:
        annotate_func = Max
    else:
        annotate_func = Min

    prices = dict(Order.open_objects.filter(
        side=side,
        symbol__enable=True,
        symbol__name__in=symbols
    ).values('symbol__name').annotate(p=annotate_func('price')).values_list('symbol__name', 'p'))

    if len(symbols) != len(prices):
        otc_spreads = get_all_otc_spreads(side)
        remaining_symbols = set(symbols) - set(prices)

        remaining_coins = set([get_symbol_parts(symbol)[0] for symbol in remaining_symbols])
        external_prices = {
            r.coin: r.price for r in fetch_external_redis_prices(remaining_coins, side, allow_stale=allow_stale) if r.price
        }

        for symbol in remaining_symbols:
            coin, base = get_symbol_parts(symbol)

            if symbol == 'IRTUSDT':
                usdt_price_other_side = get_prices([USDT_IRT], side=get_other_side(side), allow_stale=allow_stale)[USDT_IRT]
                ext_price = Decimal(1) / usdt_price_other_side
            elif coin == base:
                ext_price = Decimal(1)
            else:
                ext_price = external_prices.get(coin)

                if ext_price and base == Asset.IRT:
                    ext_price *= prices[USDT_IRT]

            if ext_price:
                prices[symbol] = ext_price * otc_spreads.get(symbol, 1)

    return prices


def get_last_prices(symbols: List[str]):
    if USDT_IRT not in symbols:
        symbols.append(USDT_IRT)

    last_prices = dict(PairSymbol.objects.filter(
        name__in=symbols,
        enable=True,
        last_trade_price__isnull=False,
    ).values_list('name', 'last_trade_price'))

    remaining_symbols = set(symbols) - set(last_prices)

    if remaining_symbols:
        remaining_coins = set([get_symbol_parts(symbol)[0] for symbol in remaining_symbols])
        external_prices = _get_external_last_prices(remaining_coins, allow_stale=True)

        for symbol in remaining_symbols:
            coin, base = get_symbol_parts(symbol)

            if symbol == 'IRTUSDT':
                last_price = Decimal(1) / last_prices[USDT_IRT]
            elif coin == base:
                last_price = Decimal(1)
            else:
                last_price = external_prices.get(coin)

                if last_price and base == Asset.IRT:
                    last_price *= last_prices[USDT_IRT]

            if last_price:
                last_prices[symbol] = last_price

    return last_prices


def get_coins_symbols(coins: List[str]) -> List[str]:
    symbols = []

    for base in (Asset.IRT, Asset.USDT):
        symbols.extend([c + base for c in coins])

    return symbols


def get_price(symbol: str, side: str, allow_stale: bool = False):
    prices = get_prices([symbol], side, allow_stale)
    return prices.get(symbol)
