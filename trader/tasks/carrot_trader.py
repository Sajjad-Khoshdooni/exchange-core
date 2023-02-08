import logging
import math
import random
from decimal import Decimal

from celery import shared_task
from decouple import config

from accounts.models import Account
from ledger.utils.external_price import get_external_price, BUY, SELL
from ledger.utils.otc import spread_to_multiplier
from ledger.utils.precision import floor_precision
from market.models import PairSymbol, Order
from trader.bots.utils import place_carrot_order, get_top_prices_exclude_system_orders

logger = logging.getLogger(__name__)

TASK_INTERVAL = 7
PER_PAIR_EXPECTED_TRADES_PER_SECOND = Decimal(1) / 30  # every 30 seconds we have at least one order


# no offense to dear traders but for more info about the name,
# see https://imgurl.ir/uploads/t28108_IMG_20220717_162148_191.jpg
@shared_task(queue='trader')
def carrot_trader():
    symbols = list(PairSymbol.objects.filter(enable=True, market_maker_enabled=True))
    choices_count = math.ceil(TASK_INTERVAL * PER_PAIR_EXPECTED_TRADES_PER_SECOND * len(symbols) * 2)

    symbols = set(random.choices(symbols, k=choices_count))

    account = get_account()
    users_top_prices = get_top_prices_exclude_system_orders([s.id for s in symbols])

    for symbol in symbols:
        symbol_top_prices = {side: users_top_prices[symbol.id, side] for side in [BUY, SELL]}
        generate_carrot_order(symbol, account, symbol_top_prices)


def get_account():
    account_id = config('BOT_CARROT_TRADER_ACCOUNT_ID')
    return Account.objects.get(id=account_id)


def generate_carrot_order(symbol: PairSymbol, account, top_prices):
    side = random.choices([BUY, SELL])[0]
    top_user_price = top_prices[side]
    top_opposite_user_price = top_prices[Order.get_opposite_side(side)]
    if top_user_price:
        price = get_external_price(
            coin=symbol.asset.symbol,
            base_coin=symbol.base_asset.symbol,
            side=side
        )

        trading_price = price * spread_to_multiplier(Decimal('0.001'), side)

        trading_price = floor_precision(trading_price, symbol.tick_size)
        if (side == BUY and top_user_price < trading_price) or \
                (side == SELL and top_user_price > trading_price):
            logger.info('placing carrot order %s %s' % (symbol, side))
            return place_carrot_order(symbol, account, side, top_user_price, top_opposite_user_price)
