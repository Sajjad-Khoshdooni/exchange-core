import logging
from decimal import Decimal
from typing import Union

from django.core.cache import caches
from django.db import models
from django.utils import timezone
from yekta_config.config import config

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.precision import floor_precision
from ledger.utils.price import BUY, SELL, get_trading_price_irt, get_trading_price_usdt
from market.models import PairSymbol
from market.utils import new_order, get_open_orders, cancel_orders

logger = logging.getLogger(__name__)

ASK, BID = SELL, BUY

ORDER_VALUE = 500_000
MA_INTERVAL = 60
MA_LENGTH = 9

cache = caches['trader']


class MovingAverage(models.Model):
    symbol = models.OneToOneField(to=PairSymbol, on_delete=models.CASCADE)
    below = models.BooleanField(default=True)
    change_date = models.DateTimeField(null=True, blank=True)
    enable = models.BooleanField(default=True)

    def log(self, msg: str):
        logger.info("MA %s: %s" % (self.symbol, msg))

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

        if self.below and median_price > avg_ask:
            # buy
            self.log('below avg crossing => buying')

            wallet = self.symbol.base_asset.get_wallet(self.get_account())

            price = floor_precision(ask * Decimal('1.03'), self.symbol.tick_size)

            balance = wallet.get_free()

            if balance < ORDER_VALUE / 10:
                self.log('ignore selling not enough balance')

            max_value = min(balance, ORDER_VALUE)
            amount = floor_precision(Decimal(max_value / ask), self.symbol.step_size)

            self.cancel_open_orders()

            self.log('buying %s with price=%s' % (amount, price))
            new_order(self.symbol, self.get_account(), amount, price, side=BUY)

            self.reverse_below()

        elif not self.below and median_price < avg_bid:
            # sell!
            self.log('above avg crossing => selling')

            price = floor_precision(bid * Decimal('0.97'), self.symbol.tick_size)

            wallet = self.symbol.asset.get_wallet(self.get_account())

            balance = wallet.get_free()

            if balance * bid < ORDER_VALUE / 10:
                self.log('ignore selling not enough balance')

            amount = floor_precision(balance, self.symbol.step_size)

            self.cancel_open_orders()

            self.log('selling %s with price=%s' % (amount, price))
            new_order(self.symbol, self.get_account(), amount, price, side=SELL)

            self.reverse_below()

    def reverse_below(self):
        self.below = not self.below
        self.change_date = timezone.now()
        self.save()

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
        key = self.get_cache_key()
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

        key = self.get_cache_key()
        prices = cache.get(key) or {}

        prices[timestamp] = {'a': ask, 'b': bid}
        prices = dict(list(prices.items())[-MA_LENGTH:])

        cache.set(key, prices)

    def get_current_price(self, side) -> Decimal:
        if self.symbol.base_asset.symbol == Asset.IRT:
            return get_trading_price_irt(self.symbol.asset.symbol, side)
        elif self.symbol.base_asset.symbol == Asset.USDT:
            return get_trading_price_usdt(self.symbol.asset.symbol, side)
        else:
            raise NotImplementedError

    def get_cache_key(self):
        return 'ma-9-60:' + str(self.symbol.name)
