import logging
import random
from decimal import Decimal
from typing import Union

from django.core.cache import caches
from django.utils import timezone
from decouple import config

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.price import BUY, SELL
from market.models import PairSymbol
from market.utils import get_open_orders, cancel_orders
from trader.bots.utils import get_current_price, random_buy, random_sell

logger = logging.getLogger(__name__)

ASK, BID = SELL, BUY

ORDER_VALUE_IRT = 150_000
ORDER_VALUE_USDT = 7

MA_INTERVAL = 60
MA_LENGTH = 15

cache = caches['trader']


class MovingAverage:
    def __init__(self, symbol: PairSymbol):
        self.symbol = symbol

    def log(self, msg: str):
        logger.info("MA %s: %s" % (self.symbol, msg))

    def update(self, dry_run: bool = False):
        ask, bid = (get_current_price(self.symbol, ASK), get_current_price(self.symbol, BID))
        median_price = (ask + bid) / 2

        self.push_prices(ask, bid)

        if random.randint(0, 2) != 0:  # throttle order
            return

        avg_prices = self.get_average_prices()

        if not avg_prices:
            self.log('ignoring due to few prices available')
            return

        avg_ask, avg_bid = avg_prices['a'], avg_prices['b']

        self.log('ask=%s, bid=%s, median=%s, avg_ask=%s, avg_bid=%s' % (ask, bid, median_price, avg_ask, avg_bid))

        below = self.is_below()

        if below and ask > avg_ask and bid > avg_bid:
            # buy
            self.log('below avg crossing => buying')

            self.cancel_open_orders()

            if random_buy(self.symbol, self.get_account()):
                self.log('bought %s' % self.symbol)
                self.set_below(False)

        elif not below and ask < avg_ask and bid < avg_bid:
            # sell!
            self.log('above avg crossing => selling')

            self.cancel_open_orders()

            if random_sell(self.symbol, self.get_account()):
                self.log('sold %s' % self.symbol)
                self.set_below(True)

    def cancel_open_orders(self):
        wallet = self.symbol.asset.get_wallet(self.get_account())
        open_orders = get_open_orders(wallet)

        if len(open_orders) > 0:
            cancel_orders(open_orders)
            self.log('%s orders canceled.' % len(open_orders))

    @classmethod
    def get_account(cls) -> Account:
        account_id = config('BOT_RANDOM_TRADER_ACCOUNT_ID')
        return Account.objects.get(id=account_id)

    def get_average_prices(self) -> Union[None, dict]:
        key = self.get_cache_history_key()
        prices_dict = cache.get(key) or {}
        prices = list(prices_dict.items())

        min_timestamp = round(timezone.now().timestamp()) // MA_INTERVAL - MA_LENGTH

        valid_prices = list(filter(lambda p: p[0] >= min_timestamp, prices))

        if len(valid_prices) < MA_LENGTH * 0.6:
            return

        return {
            'a': sum(map(lambda p: p[1]['a'], valid_prices)) / len(valid_prices),
            'b': sum(map(lambda p: p[1]['b'], valid_prices)) / len(valid_prices)
        }

    def push_prices(self, ask: Decimal, bid: Decimal):
        timestamp = round(timezone.now().timestamp()) // MA_INTERVAL

        key = self.get_cache_history_key()
        prices = cache.get(key) or {}

        prices[timestamp] = {'a': ask, 'b': bid}
        prices = dict(list(prices.items())[-MA_LENGTH:])

        cache.set(key, prices, 1000)

    def get_cache_history_key(self):
        return 'ma-9-60:' + str(self.symbol.name)

    def get_cache_below_key(self):
        return 'ma-9-60:' + str(self.symbol.name) + ':below'

    def is_below(self) -> bool:
        b = cache.get(self.get_cache_below_key())
        if b is None:
            return True
        else:
            return b

    def set_below(self, value):
        cache.set(self.get_cache_below_key(), value, None)
