import math
from abc import ABC
from decimal import Decimal

from django.conf import settings

from ledger.utils.precision import decimal_to_str
from ledger.utils.price import get_trading_price_usdt, get_spread, get_price, get_other_side
from provider.exchanges.interface.binance_interface import ExchangeHandler, MARKET, SELL, BUY, LIMIT, HOUR
from provider.exchanges.sdk.mexc_sdk import mexc_send_sign_request, mexc_send_public_request


class MexcSpotHandler(ExchangeHandler):
    NAME = 'mexc'
    MARKET_TYPE = 'spot'

    def _collect_api(self, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        # if settings.DEBUG_OR_TESTING:
        #     return {}
        data = data or {}

        if signed:
            return mexc_send_sign_request(http_method=method, url_path=url, payload=data)
        else:
            return mexc_send_public_request(http_method=method, url_path=url, payload=data)

    @classmethod
    def rename_network_symbol_from_mexc_to_origin(cls, network_symbol: str):
        rename_list = {
            'TRC20': 'TRX',
            'BEP20(BSC)': 'BSC'
        }
        return rename_list.get(network_symbol, network_symbol)

    @classmethod
    def rename_network_symbol_from_origin_to_mexc(cls, network_symbol: str):
        rename_list = {
            'TRX': 'TRC20',
            'BSC': 'BEP20(BSC)'
        }
        return rename_list.get(network_symbol, network_symbol)

    def get_trading_symbol(self, coin: str):
        coin = self.rename_big_coin_to_coin(coin)
        return coin+'USDT'

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = LIMIT,
                    client_order_id: str = None) -> dict:

        coin = self.rename_coin_to_big_coin(symbol[:-4])
        coin_coefficient = self.get_coin_coefficient(symbol)
        price_init = get_price(coin=coin, side=side)
        value = amount * price_init
        trading_price = decimal_to_str(get_trading_price_usdt(coin=coin, side=get_other_side(side.lower()), value=value)/ coin_coefficient/2)

        order_url = '/api/v3/order'

        side = side.upper()
        order_type = order_type.upper()

        size = decimal_to_str(Decimal(amount) * Decimal(coin_coefficient))

        assert side in (SELL, BUY)
        assert order_type in (MARKET, LIMIT)

        data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': size,
            'price': trading_price
        }
        resp = self._collect_api(url=order_url, method='POST', data=data, signed=True)
        print(resp)
        return resp

    def get_account_details(self):
        return self.collect_api(url='/api/v3/account', method='GET') or {}

    def get_free_dict(self):
        balances_list = self.get_account_details()['balances']
        resp = {}
        for b in balances_list:
            coin = self.rename_coin_to_big_coin(b['asset'])
            coin_coefficient = self.get_coin_coefficient(coin)
            amount = Decimal(b['free']) / coin_coefficient
            resp[coin] = amount
        return resp

    def get_all_coins(self):
        return self.collect_api('/api/v3/capital/config/getall', method='GET', signed=True, cache_timeout=HOUR)

    def get_coin_data(self, coin: str):

        coin = self.rename_big_coin_to_coin(coin)
        info = list(filter(lambda d: d['coin'] == coin, self.get_all_coins()))
        coin_coefficient = self.get_coin_coefficient(coin)
        if not info:
            return
        else:
            network_list = info[0].get('networkList')

            data = {'networkList': []}
            for chain in network_list:
                data['networkList'].append({
                    'network': self.rename_network_symbol_from_mexc_to_origin(chain['network'].upper()),
                    'name': chain['name'],
                    'kucoin_name': '',
                    'addressRegex': '',
                    'minConfirm': chain.get('minConfirm'),
                    'unLockConfirm': '0',
                    'withdrawFee': decimal_to_str(Decimal(chain.get('withdrawFee'))/coin_coefficient),
                    'withdrawMin': decimal_to_str((Decimal((chain.get('withdrawMin'))) + Decimal(chain.get('withdrawFee')))
                                                  / coin_coefficient),
                    'withdrawMax': decimal_to_str(Decimal(chain.get('withdrawMax', '100000000000')) / coin_coefficient),
                    'withdrawIntegerMultiple': Decimal('1e-{}'.format(chain.get('withdrawIntegerMultiple') or '0')),
                    'withdrawEnable': chain.get('withdrawEnable')

                })
        return data

    def get_network_info(self, coin: str, network):

        chains = self.get_coin_data(coin=coin).get('networkList')

        info = list(filter(lambda d: d['network'] == network.symbol, chains))
        if info:
            return info[0]
        return

    def get_withdraw_fee(self, coin: str, network):
        info = self.get_network_info(coin, network)
        return Decimal(info.get('withdrawFee'))

    def get_symbol_data(self, symbol: str):
        symbol_coefficient = self.get_coin_coefficient(symbol)
        coin_data = self.collect_api('/api/v3/exchangeInfo?symbol={}'.format(symbol), method='GET', signed=False)
        coin_data = coin_data.get('symbols')[0]
        if not coin_data:
            return

        resp = {'filters': [
            {
                'filterType': 'LOT_SIZE',
                'stepSize': Decimal('1e-{}'.format(coin_data.get('baseAssetPrecision') + Decimal(math.log10(symbol_coefficient)))),
                'minQty': '0',
                'maxQty': '0'
            },
            {
                'filterType': 'PRICE_FILTER',
                'tickSize': '1e-{}'.format(Decimal(coin_data.get('quoteAssetPrecision')) - Decimal(math.log10(symbol_coefficient))),
            }
        ]}
        if coin_data.get('isSpotTradingAllowed'):
            resp['status'] = 'TRADING'
        return resp

    def get_step_size(self, symbol: str) -> Decimal:
        data = self.get_symbol_data(symbol=symbol)
        lot_size = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', data['filters']))[0]
        return Decimal(lot_size['stepSize'])

    def get_lot_min_quantity(self, symbol: str) ->Decimal:
        return Decimal(0)

    def get_orderbook(self, symbol: str):
        data = {
            'symbol': symbol,
        }
        resp = self.collect_api(url='/api/v3/ticker/bookTicker', data=data, method='GET', signed=False)
        resp_data = {
            'bestAsk': resp['askPrice'],
            'bestBid': resp['bidPrice'],
            'symbol': symbol,
        }
        return resp_data

    def get_spot_handler(self) -> 'ExchangeHandler':
        return self

    def get_min_notional(self):
        return Decimal(5)


class MexcFuturesHandler(MexcSpotHandler):
    pass