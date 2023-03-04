import logging
import math
import random
from decimal import Decimal

from celery import shared_task
from decouple import config

from accounts.models import Account
from ledger.utils.external_price import BUY, SELL
from market.models import PairSymbol
from market.models.order import CancelOrder, Order
from market.utils.order_utils import get_market_top_price_amounts
from market.utils.redis import get_daily_order_size_factors
from trader.bots.utils import get_top_prices_exclude_system_orders, random_buy, random_sell

logger = logging.getLogger(__name__)

TASK_INTERVAL = 17
PER_PAIR_EXPECTED_TRADES_PER_SECOND = Decimal(1) / 180  # every 3 min we have at least one order


@shared_task(queue='trader')
def random_trader():
    symbols = list(PairSymbol.objects.filter(enable=True, market_maker_enabled=True))
    choices_count = math.ceil(TASK_INTERVAL * PER_PAIR_EXPECTED_TRADES_PER_SECOND * len(symbols) * 2)

    symbols = set(random.choices(symbols, k=choices_count))

    account = get_account()
    daily_factors = get_daily_order_size_factors(symbol_ids=list(map(lambda s: s.id, symbols)))
    system_top_price_amounts = get_market_top_price_amounts(
        order_types_in=(Order.DEPTH, Order.BOT),
        symbol_ids=list(map(lambda s: s.id, symbols))
    )
    users_top_prices = get_top_prices_exclude_system_orders([s.id for s in symbols])

    for symbol in symbols:
        top_price_amounts = {
            side: system_top_price_amounts[(symbol.id, side)] for side in (BUY, SELL)
        }
        user_top_prices = {side: users_top_prices[symbol.id, side] for side in [BUY, SELL]}
        random_trade(symbol, account, top_price_amounts, user_top_prices, daily_factors[symbol.id])


def get_account():
    account_id = config('BOT_RANDOM_TRADER_ACCOUNT_ID')
    return Account.objects.get(id=account_id)


def random_trade(symbol: PairSymbol, account, top_price_amounts, user_top_prices, daily_factor: int):
    logger.info(f'random trading {symbol} ({top_price_amounts}) {daily_factor}')

    available_choices = []
    random_funcs = {BUY: random_sell, SELL: random_buy}

    for side in (BUY, SELL):
        if top_price_amounts[side]['price'] and top_price_amounts[side]['price'] != user_top_prices[side]:
            available_choices.append(
                (random_funcs[side], top_price_amounts[side]['amount'], top_price_amounts[side]['price'])
            )

    if not available_choices:
        logger.info(f'skip random trading {symbol}')
        return

    random_func, max_amount, market_price = random.choices(available_choices)[0]

    try:
        logger.info(f'random trading {symbol} {random_func.__name__}')
        random_func(symbol, account, max_amount, market_price, daily_factor)
    except CancelOrder as e:
        logger.info(e)
