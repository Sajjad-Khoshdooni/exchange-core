import logging
import math
import random
from decimal import Decimal

from celery import shared_task
from yekta_config.config import config

from accounts.models import Account
from market.models import PairSymbol
from market.utils import new_order
from trader.bots.moving_average import MovingAverage
from trader.bots.utils import balance_tether, random_buy, random_sell

logger = logging.getLogger(__name__)


TASK_INTERVAL = 60
PER_PAIR_EXPECTED_TRADES_PER_SECOND = Decimal(1) / 300  # every 5 min we have at least one order


@shared_task(queue='random_trader')
def random_trader():
    symbols = list(PairSymbol.objects.filter(enable=True, market_maker_enabled=True))
    choices_count = math.ceil(TASK_INTERVAL * PER_PAIR_EXPECTED_TRADES_PER_SECOND * len(symbols) * 2)

    symbols = set(random.choices(symbols, k=choices_count))

    account = get_account()

    for symbol in symbols:
        random_trade(symbol, account)


def get_account():
    account_id = config('BOT_RANDOM_TRADER_ACCOUNT_ID')
    return Account.objects.get(id=account_id)


def random_trade(symbol: PairSymbol, account):
    logger.info('random trading %s' % symbol)

    random_func = random.choices([random_buy, random_sell])[0]
    random_func(symbol, account)
