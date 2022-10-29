import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import log10
from typing import List, Dict

import requests
from decouple import config
from django.conf import settings
from django.db.models import Sum
from pydantic.decorator import validate_arguments
from urllib3.exceptions import ReadTimeoutError

from accounts.verifiers.jibit import Response
from ledger.exceptions import HedgeError
from ledger.models import Asset, Network, Wallet, Transfer
from ledger.utils.fields import DONE
from ledger.utils.precision import floor_precision
from ledger.utils.price import SELL, BUY, get_trading_price_usdt

TRADE, BORROW, LIQUIDATION, WITHDRAW, HEDGE, PROVIDE_BASE, FAKE = \
    'trade', 'borrow', 'liquid', 'withdraw', 'hedge', 'prv-base', 'fake'

logger = logging.getLogger(__name__)

SPOT, FUTURES = 'spot', 'futures'
BINANCE, KUCOIN, MEXC = 'binance', 'kucoin', 'mexc'


@validate_arguments
@dataclass
class MarketInfo:
    coin: str
    base_coin: str
    exchange: str

    type: str  # spot | futures

    step_size: Decimal
    min_quantity: Decimal
    max_quantity: Decimal

    min_notional: Decimal


@validate_arguments
@dataclass
class FuturesInfo:
    asset: Asset
    notional: Decimal
    position_amount: Decimal


@validate_arguments
@dataclass
class CoinOrders:
    coin: str
    buy: Decimal
    sell: Decimal


@validate_arguments
@dataclass
class NetworkInfo:
    coin: str
    network: str

    withdraw_min: Decimal
    withdraw_max: Decimal
    withdraw_fee: Decimal
    withdraw_enable: bool


@validate_arguments
@dataclass
class WithdrawStatus:
    status: str
    tx_id: str

    @classmethod
    def init(cls, data: dict):
        return WithdrawStatus(
            status=data['status'],
            tx_id=data.get('tx_id')
        )


@validate_arguments
@dataclass
class CoinInfo:
    coin: str = ''
    price: float = 0
    change_24h: float = 0
    volume_24h: float = 0
    change_7d: float = 0
    high_24h: float = 0
    low_24h: float = 0
    change_1h: float = 0
    cmc_rank: int = 0
    market_cap: float = 0
    circulating_supply: float = 0
    weekly_trend_url: str = ''


class ProviderRequester:
    def collect_api(self, path: str, method: str = 'GET', data: dict = None) -> Response:
        if data is None:
            data = {}

        url = config('PROVIDER_BASE_URL', default='https://provider.raastin.com') + path

        request_kwargs = {
            'url': url,
            # 'timeout': 60,
            'headers': {'Authorization': config('PROVIDER_TOKEN')},
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)
        except (requests.exceptions.ConnectionError, ReadTimeoutError, requests.exceptions.Timeout):
            raise TimeoutError

        print('PROVIDER', path, method, data, resp.json())

        return Response(data=resp.json(), success=resp.ok, status_code=resp.status_code)

    def get_total_orders_amount_sum(self, asset: Asset = None) -> List[CoinOrders]:
        if asset:
            data = {'coin': asset.symbol}
        else:
            data = {}

        resp = self.collect_api('/api/v1/orders/total/', data=data)
        assert resp.success

        coin_orders_data_map = defaultdict(dict)
        for order_data in resp.data:
            coin = order_data['coin']
            side = order_data['side']
            amount = Decimal(order_data['amount'])

            coin_orders_data_map[coin][side] = amount

        orders = []

        for coin, orders_data in coin_orders_data_map.items():
            orders.append(CoinOrders(
                coin=coin,
                buy=Decimal(orders_data.get('buy', 0)),
                sell=Decimal(orders_data.get('sell', 0)),
            ))

        return orders

    def get_hedge_amount(self, asset: Asset, coin_order: CoinOrders = None) -> Decimal:
        """
        how much assets we have more!

        out = -internal - binance transfer deposit
        hedge = all assets - users = (internal + binance manual deposit + binance withdraw + binance trades)
                + system + out = system + binance trades + binance manual deposit

        given binance manual deposit = 0 -> hedge = system + binance manual deposit + binance trades
        """
        from accounts.models import Account

        system_balance = Wallet.objects.filter(
            account__type=Account.SYSTEM,
            asset=asset
        ).aggregate(
            sum=Sum('balance')
        )['sum'] or 0

        if not coin_order:
            coin_order = next(iter(self.get_total_orders_amount_sum(asset)), None)

        orders_diff = 0

        if coin_order:
            orders_diff = coin_order.buy - coin_order.sell

        return system_balance + orders_diff

    def get_market_info(self, asset: Asset) -> MarketInfo:
        resp = self.collect_api('/api/v1/market/', data={'coin': asset.symbol})
        return MarketInfo(coin=asset.symbol, **resp.data)

    def get_spot_balance_map(self, exchange) -> dict:
        resp = self.collect_api('/api/v1/spot/balance/', data={'exchange': exchange})
        return resp.data

    def get_futures_info(self, exchange: str) -> dict:
        resp = self.collect_api('/api/v1/futures/', data={'exchange': exchange})
        return resp.data

    def get_network_info(self, asset: Asset, network: Network) -> NetworkInfo:
        resp = self.collect_api('/api/v1/networks/', data={'coin': asset.symbol, 'network': network.symbol})
        return NetworkInfo(**resp.data)

    def try_hedge_new_order(self, asset: Asset, scope: str, amount: Decimal = 0, side: str = ''):
        assert amount >= 0
        if amount > 0:
            assert side

        if settings.DEBUG_OR_TESTING_OR_STAGING:
            logger.info('ignored due to debug')
            return

        if not asset.hedge:
            logger.info('ignored due to no hedge method')
            return

        to_buy = amount if side == BUY else -amount
        hedge_amount = self.get_hedge_amount(asset) - to_buy

        market_info = self.get_market_info(asset)

        step_size = market_info.step_size

        # Hedge strategy: don't sell assets ASAP and hold them!

        if hedge_amount < 0:
            threshold = step_size / 2
        else:
            threshold = step_size * 2

        if abs(hedge_amount) > threshold:
            side = SELL

            if hedge_amount < 0:
                hedge_amount = -hedge_amount
                side = BUY

            round_digits = -int(log10(step_size))

            order_amount = round(hedge_amount, round_digits)

            price = get_trading_price_usdt(asset.symbol, side=BUY)
            min_notional = market_info.min_notional * Decimal('1.1')

            if order_amount * price < min_notional:
                logger.info('ignored due to small order')
                return

            if market_info.type == 'spot' and side == SELL:
                balance_map = self.get_spot_balance_map(market_info.exchange)
                balance = balance_map[asset.symbol]

                if balance < order_amount:
                    diff = order_amount - balance

                    if diff * price < min_notional:
                        order_amount = floor_precision(balance, round_digits)

                        if order_amount * price < min_notional:
                            logger.info('ignored due to small order')
                            return

            if side == BUY and market_info.base_coin == 'BUSD':
                busd_balance = self.get_spot_balance_map(market_info.exchange)['BUSD']
                needed_busd = order_amount * price

                if needed_busd > busd_balance:
                    logger.info('providing busd for order')
                    to_buy_busd = max(math.ceil((needed_busd - busd_balance) * Decimal('1.01')), min_notional)

                    self.new_order(
                        asset=Asset.objects.get('BUSD'),
                        side=BUY,
                        amount=Decimal(to_buy_busd),
                        scope='prv-base',
                    )

            order = self.new_order(asset, side, order_amount, scope)

            if not order:
                raise HedgeError

    def new_order(self, asset: Asset, scope: str, amount: Decimal, side: str):
        return self.collect_api('/api/v1/orders/', method='POST', data={
            'coin': asset.symbol,
            'scope': scope,
            'amount': str(amount),
            'side': side
        })

    def new_withdraw(self, transfer: Transfer):
        assert not transfer.deposit

        resp = self.collect_api('/api/v1/withdraw/', method='POST', data={
            'coin': transfer.asset.symbol,
            'network': transfer.network.symbol,
            'amount': str(transfer.amount),
            'address': transfer.out_address,
            'memo': transfer.memo,
            'requester_id': transfer.id,
        })

        if not resp.success:
            logger.error('Failed to provider withdraw', extra={
                'resp': resp.data
            })

        return resp.success

    def new_hedged_spot_buy(self, asset: Asset, amount: Decimal, spot_side: str, caller_id: str):
        self.collect_api('/api/v1/orders/hedged/', method='POST', data={
            'coin': asset.symbol,
            'amount': str(amount),
            'requester_id': caller_id
        })

    def get_transfer_status(self, transfer: Transfer) -> WithdrawStatus:
        resp = self.collect_api('/api/v1/withdraw/%d/' % transfer.id)
        return WithdrawStatus.init(resp.data['status'])

    # todo: add caching
    def get_coins_info(self, coins: List[str] = None) -> Dict[str, CoinInfo]:
        resp = self.collect_api('/api/v1/coins/info/')

        coins_info = {}

        for info_data in resp.data:
            info = CoinInfo(**info_data)
            coins_info[info.coin] = info

        return coins_info

    def get_price(self, symbol: str, side: str, delay: int = 300, when: datetime = None) -> Decimal:
        resp = self.collect_api('/api/v1/market/price/history/', data={
            'symbol': symbol,
            'side': side,
            'delay': delay,
            'datetime': when
        })

        if resp.success:
            return Decimal(resp.data['price'])

    def get_avg_trade_price(self, symbol: str, start: datetime, end: datetime) -> Decimal:
        resp = self.collect_api('/api/v1/market/price/trade/avg/', data={
            'symbol': symbol,
            'start': start,
            'end': end
        })

        if resp.success:
            return Decimal(resp.data['price'])


class MockProviderRequester(ProviderRequester):
    def get_total_orders_amount_sum(self, asset: Asset = None) -> List[CoinOrders]:
        return []

    def get_hedge_amount(self, asset: Asset, coin_orders: CoinOrders = None) -> Decimal:
        return Decimal(0)

    def get_market_info(self, asset: Asset) -> MarketInfo:
        return MarketInfo(
            coin=asset.symbol,
            base_coin=Asset.USDT,
            exchange='binance',
            type='spot',
            step_size=Decimal(1),
            min_quantity=Decimal(1),
            max_quantity=Decimal(1000),
            min_notional=Decimal(10)
        )

    def get_spot_balance_map(self, exchange) -> dict:
        return {}

    def get_futures_info(self, exchange: str) -> dict:
        return {}

    def get_network_info(self, asset: Asset, network: Network) -> NetworkInfo:
        return NetworkInfo(
            coin=asset.symbol,
            network=network.symbol,
            withdraw_min=Decimal(1),
            withdraw_max=Decimal(100),
            withdraw_fee=Decimal(1),
            withdraw_enable=True
        )

    def try_hedge_new_order(self, asset: Asset, scope: str, amount: Decimal = 0, side: str = ''):
        pass

    def new_order(self, asset: Asset, scope: str, amount: Decimal, side: str):
        return True

    def new_withdraw(self, transfer: Transfer):
        return True

    def new_hedged_spot_buy(self, asset: Asset, amount: Decimal, spot_side: str, caller_id: str):
        pass

    def get_transfer_status(self, transfer: Transfer) -> WithdrawStatus:
        return WithdrawStatus(status=DONE, tx_id='tx')

    def get_coins_info(self, coins: List[str] = None) -> Dict[str, CoinInfo]:
        return {}

    def get_price(self, symbol: str, side: str, delay: int = 300, when: datetime = None) -> Decimal:
        return Decimal(30000)

    def get_avg_trade_price(self, symbol: str, start: datetime, end: datetime) -> Decimal:
        return Decimal(30000)


def get_provider_requester() -> ProviderRequester:
    if settings.DEBUG_OR_TESTING:
        return MockProviderRequester()
    else:
        return ProviderRequester()
