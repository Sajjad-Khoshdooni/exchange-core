import logging
import math
import random
from decimal import Decimal

from celery import shared_task
from yekta_config.config import config

from accounts.models import Account
from market.models import PairSymbol
from market.models.order import CancelOrder
from market.utils.redis import get_daily_order_size_factors
from trader.bots.utils import random_buy, random_sell

logger = logging.getLogger(__name__)


TASK_INTERVAL = 17
PER_PAIR_EXPECTED_TRADES_PER_SECOND = Decimal(1) / 180  # every 3 min we have at least one order


@shared_task(queue='random_trader')
def random_trader():
    symbols = list(PairSymbol.objects.filter(enable=True, market_maker_enabled=True))
    choices_count = math.ceil(TASK_INTERVAL * PER_PAIR_EXPECTED_TRADES_PER_SECOND * len(symbols) * 2)

    symbols = set(random.choices(symbols, k=choices_count))

    account = get_account()
    daily_factors = get_daily_order_size_factors(symbol_ids=list(map(lambda s: s.id, symbols)))

    for symbol in symbols:
        random_trade(symbol, account, daily_factors[symbol.id])


def get_account():
    account_id = config('BOT_RANDOM_TRADER_ACCOUNT_ID')
    return Account.objects.get(id=account_id)


def random_trade(symbol: PairSymbol, account, daily_factor: int):
    logger.info('random trading %s' % symbol)

    random_func = random.choices([random_buy, random_sell])[0]

    try:
        random_func(symbol, account, daily_factor)
    except CancelOrder as e:
        logger.info(e)
