from ledger.utils.cache import cache_for
from market.models import PairSymbol


@cache_for()
def get_symbol_prices():
    last_prices = dict(PairSymbol.objects.filter(enable=True).values_list('id', 'last_trade_price'))
    return {
        'last': last_prices,
        'yesterday': last_prices
    }
