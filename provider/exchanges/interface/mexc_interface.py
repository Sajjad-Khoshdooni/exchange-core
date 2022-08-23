from abc import ABC
from decimal import Decimal

from django.conf import settings

from ledger.utils.precision import decimal_to_str
from ledger.utils.price import get_trading_price_usdt
from provider.exchanges.interface.binance_interface import ExchangeHandler, MARKET, SELL, BUY, LIMIT
from provider.exchanges.sdk.mexc_sdk import mexc_send_sign_request, mexc_send_public_request


class MexcSpotHandler(ExchangeHandler):
    NAME = 'mexc'

    def _collect_api(self, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        # if settings.DEBUG_OR_TESTING:
        #     return {}
        # data = data or {}

        if signed:
            return mexc_send_sign_request(http_method=method, url_path=url, payload=data)
        else:
            return mexc_send_public_request(http_method=method, url_path=url, payload=data)

    def get_trading_symbol(self, coin: str):
        coin = self.rename_big_coin_to_coin(coin)
        return coin+'USDT'

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:
        order_url = '/api/v3/order'
        coin_coefficient = self.get_coin_coefficient(symbol)
        side = side.upper()
        order_type = order_type.upper()

        size = decimal_to_str(Decimal(amount) * Decimal(coin_coefficient))

        assert side in (SELL, BUY)
        assert order_type in (MARKET, LIMIT)

        data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
        }
        if side == BUY:
            coin = self.rename_coin_to_big_coin(symbol[:-4])
            price = get_trading_price_usdt(coin=coin, side=SELL.lower(), raw_price=True)
            quoteOrderQty = price * Decimal(size)
            data['quoteOrderQty'] =decimal_to_str(quoteOrderQty)

        else:
            data['quantity'] = size
        return self._collect_api(url=order_url, method='POST', data=data, signed=True)

    def get_orderbook(self, symbol: str):
        data = {
            'symbol': symbol,
            'limit': 1
        }
        resp = self.collect_api(url='/api/v3/depth', method='GET', data=data, signed=False)
        data = {
            'bestAsk': resp['asks'][0][0],
            'bestBid': resp['bids'][0][0],
            'symbol': symbol,
        }
        return data

class MexcFuturesHandler(MexcSpotHandler):
    pass