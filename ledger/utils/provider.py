import logging
import math
from dataclasses import dataclass
from decimal import Decimal
from math import log10

import requests
from django.conf import settings
from django.db.models import Sum
from urllib3.exceptions import ReadTimeoutError
from yekta_config import secret
from yekta_config.config import config

from accounts.models import Account
from accounts.verifiers.jibit import Response
from ledger.exceptions import HedgeError
from ledger.models import Asset, Network, Wallet, Transfer
from ledger.utils.precision import floor_precision
from ledger.utils.price import SELL, BUY, get_trading_price_usdt

TRADE, BORROW, LIQUIDATION, WITHDRAW, HEDGE, PROVIDE_BASE, FAKE = \
    'trade', 'borrow', 'liquid', 'withdraw', 'hedge', 'prv-base', 'fake'

logger = logging.getLogger(__name__)

SPOT, FUTURES = 'spot', 'futures'
BINANCE, KUCOIN, MEXC = 'binance', 'kucoin', 'mexc'

@dataclass
class MarketInfo:
    asset: Asset
    base_asset: Asset
    exchange: str

    type: str  # spot | futures

    step_size: Decimal
    min_quantity: Decimal
    max_quantity: Decimal

    min_notional: Decimal


@dataclass
class FuturesInfo:
    asset: Asset
    notional: Decimal
    position_amount: Decimal


@dataclass
class NetworkInfo:
    asset: Asset
    network: Network

    withdraw_min: Decimal
    withdraw_max: Decimal
    withdraw_fee: Decimal
    withdraw_enable: bool


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


class ProviderRequester:

    def collect_api(self, path: str, method: str = 'GET', data: dict = None) -> Response:
        if data is None:
            data = {}

        url = config('PROVIDER_BASE_URL') + path

        request_kwargs = {
            'url': url,
            'timeout': 60,
            'headers': {'Authorization': secret('PROVIDER_TOKEN')},
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)
        except (requests.exceptions.ConnectionError, ReadTimeoutError, requests.exceptions.Timeout):
            raise TimeoutError

        return Response(data=resp.json(), success=resp.ok)

    def get_total_orders_amount_sum(self, asset: Asset) -> dict:
        resp = self.collect_api('api/v1/orders/total/', data={'coin': asset.symbol})
        return resp.data

    def get_hedge_amount(self, asset: Asset):
        """
        how much assets we have more!

        out = -internal - binance transfer deposit
        hedge = all assets - users = (internal + binance manual deposit + binance withdraw + binance trades)
                + system + out = system + binance trades + binance manual deposit

        given binance manual deposit = 0 -> hedge = system + binance manual deposit + binance trades
        """

        system_balance = Wallet.objects.filter(
            account__type=Account.SYSTEM,
            asset=asset
        ).aggregate(
            sum=Sum('balance')
        )['sum'] or 0

        orders = self.get_total_orders_amount_sum(asset)

        orders_amount = 0

        for order in orders:
            amount = order['amount']

            if order['side'] == SELL:
                amount = -amount

            orders_amount += amount

        return system_balance + orders_amount

    def get_market_info(self, asset: Asset) -> MarketInfo:
        resp = self.collect_api('/api/v1/market/', data={'coin': asset.symbol})
        base_asset = Asset.get(symbol=resp.data.pop('base_asset'))
        return MarketInfo(asset=asset, base_asset= base_asset, **resp.data)

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

            if side == BUY and market_info.base_asset.symbol == 'BUSD':
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
        return self.collect_api('api/v1/orders/', method='POST', data={
            'coin': asset.symbol,
            'scope': scope,
            'amount': amount,
            'side': side
        })

    def new_withdraw(self, transfer: Transfer):
        assert not transfer.deposit

        resp = self.collect_api('api/v1/withdraw/', method='POST', data={
            'coin': transfer.asset.symbol,
            'network': transfer.network.symbol,
            'amount': transfer.amount,
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
        self.collect_api('api/v1/orders/hedged/', method='POST', data={
            'coin': asset.symbol,
            'amount': amount,
            'requester_id': caller_id
        })

    def get_transfer_status(self, transfer: Transfer) -> WithdrawStatus:
        resp = self.collect_api('api/v1/withdraw/%d/' % transfer.id)
        return WithdrawStatus.init(resp.data['status'])
