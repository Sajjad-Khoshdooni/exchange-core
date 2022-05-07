import logging
import random
from decimal import Decimal
from typing import Union

from django.core.cache import caches
from django.utils import timezone
from yekta_config.config import config

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.precision import floor_precision
from ledger.utils.price import BUY, SELL, get_trading_price_irt, get_trading_price_usdt
from market.models import PairSymbol, Order
from market.utils import new_order, get_open_orders, cancel_orders

logger = logging.getLogger(__name__)

ASK, BID = SELL, BUY

ORDER_VALUE_IRT = 150_000
ORDER_VALUE_USDT = 7

MA_INTERVAL = 60
MA_LENGTH = 3

cache = caches['trader']


class MovingAverage:
    def __init__(self, symbol: PairSymbol):
        self.symbol = symbol

    def log(self, msg: str):
        logger.info("MA %s: %s" % (self.symbol, msg))

    @property
    def order_value_step(self):
        if self.symbol.base_asset.symbol == Asset.IRT:
            return ORDER_VALUE_IRT
        else:
            return ORDER_VALUE_USDT

    def update(self, dry_run: bool = False):
        ask, bid = (self.get_current_price(ASK), self.get_current_price(BID))
        median_price = (ask + bid) / 2

        self.push_prices(ask, bid)

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

            wallet = self.symbol.base_asset.get_wallet(self.get_account())

            price = floor_precision(ask * Decimal('1.03'), self.symbol.tick_size)

            balance = wallet.get_free()

            max_value = min(balance, random.randint(self.order_value_step, self.order_value_step * 5))
            amount = floor_precision(Decimal(max_value / ask), self.symbol.step_size)

            self.cancel_open_orders()

            if new_order(self.symbol, self.get_account(), amount, price, side=BUY, raise_exception=False):
                self.log('buying %s with price=%s' % (amount, price))
                self.set_below(False)

        elif not below and ask < avg_ask and bid < avg_bid:
            # sell!
            self.log('above avg crossing => selling')

            price = floor_precision(bid * Decimal('0.97'), self.symbol.tick_size)

            wallet = self.symbol.asset.get_wallet(self.get_account())

            balance = wallet.get_free()

            if self.symbol.name == 'USDTIRT':
                last_buy = Order.objects.filter(
                    wallet=wallet,
                    side=Order.BUY
                ).order_by('-created').first()

                if last_buy:
                    balance = min(balance, last_buy.filled_amount)

            amount = floor_precision(balance, self.symbol.step_size)

            self.cancel_open_orders()

            if new_order(self.symbol, self.get_account(), amount, price, side=SELL, raise_exception=False):
                self.log('selling %s with price=%s' % (amount, price))
                self.set_below(True)

    def cancel_open_orders(self):
        wallet = self.symbol.asset.get_wallet(self.get_account())
        open_orders = get_open_orders(wallet)

        if len(open_orders) > 0:
            cancel_orders(open_orders)
            self.log('%s orders canceled.' % len(open_orders))

    def get_account(self) -> Account:
        account_id = config('BOT_MOVING_AVERAGE_ACCOUNT_ID')
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

        cache.set(key, prices)

    def get_current_price(self, side) -> Decimal:
        if self.symbol.name.endswith(Asset.IRT):
            base_symbol = Asset.IRT
            get_trading_price = get_trading_price_irt
        elif self.symbol.name.endswith(Asset.USDT):
            base_symbol = Asset.USDT
            get_trading_price = get_trading_price_irt
        else:
            raise NotImplementedError
        coin = self.symbol.name.split(base_symbol)[0]
        return get_trading_price(coin, side)

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
        cache.set(self.get_cache_below_key(), value)
