
from decimal import Decimal

from ledger.utils.precision import decimal_to_str
from provider.exchanges.interface.binance_interface import ExchangeHandler, SELL, BUY, MARKET, LIMIT, HOUR
from provider.exchanges.sdk.kucoin_sdk import kucoin_spot_send_signed_request, kucoin_spot_send_public_request


class KucoinSpotHandler(ExchangeHandler):

    order_url = '/api/v1/orders'
    MARKET_TYPE = 'spot'

    _base_api_url = None
    _session = None

    api_path = None
    exchange = None

    @classmethod
    def collect_api(cls, url: str, method: str = 'POST', data: dict = None, signed: bool = True,
                    cache_timeout: int = None):

        cache_key = None

        # if cache_timeout:
        #     cache_key = get_cache_func_key(cls, url, method, data, signed)
        #     result = cache.get(cache_key)
        #
        #     if result is not None:
        #         return result

        result = cls._collect_api(url=url, method=method, data=data, signed=signed)

        # if cache_timeout:
        #     cache.set(cache_key, result, cache_timeout)

        return result

    @classmethod
    def _collect_api(cls, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        # if settings.DEBUG_OR_TESTING:
        #     return {}

        data = data or {}

        if signed:
            return kucoin_spot_send_signed_request(method, url, data=data)
        else:
            return kucoin_spot_send_public_request(url, data=data)

    @classmethod
    def place_order(cls, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:

        side = side.upper()
        order_type = order_type.upper()

        assert side in (SELL, BUY)
        assert order_type in (MARKET, LIMIT)

        data = {
            'symbol': symbol,
            'side': side.lower(),
            'type': order_type.lower(),
            'size': decimal_to_str(amount),
        }

        if client_order_id:
            data['clientOid'] = client_order_id

        return (cls.collect_api(url=cls.order_url, data=data) or {})

    @classmethod
    def get_account_details(cls):
        return cls.collect_api(url='/api/v1/accounts', method='GET') or {}

    @classmethod
    def withdraw(cls, coin: str, network: str, address: str, amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:

        data = {
            'currency': coin,
            'address': address,
            'amount': decimal_to_str(amount),
            'network': network,
            'memo': address_tag,
            'withdrawOrderId': client_id
        }
        return cls.collect_api('/api/v1/withdrawals', method='POST', data=data)

    @classmethod
    def get_all_coins(cls):
        return cls.collect_api('/api/v1/currencies', method='GET', cache_timeout=HOUR)

    @classmethod
    def get_coin_data(cls, coin: str):
        # info = list(filter(lambda d: d['currency'] == coin, cls.get_all_coins().json().get('data')))
        # if not info:
        #     return
        #
        # return info[0]
        return cls.collect_api('/api/v2/currencies/{}'.format(coin),
                               method='GET',
                               cache_timeout=HOUR).json().get('data', {})

    @classmethod
    def get_network_info(cls, coin: str, network: str):
        chains = cls.get_coin_data(coin=coin).get('chains')
        info = list(filter(lambda d: d['chainName'] == network, chains))
        return info

    @classmethod
    def get_withdraw_fee(cls, coin: str, network: str):
        info = cls.get_network_info(coin, network)
        return Decimal(info[0].get('withdrawalMinFee'))

    @classmethod
    def transfer(cls, asset: str, amount: float, to: str, clientOid:str, _from='mian'):
        return cls.collect_api(
            f'/api/v2/accounts/inner-transfer',
            method='POST',
            data={
                'clientOid': clientOid,
                'currency': asset,
                'from': _from,
                'to': to,
                'amount': amount,
            }
        )
    @classmethod
    def get_symbol_data(cls, symbol: str):
        data = cls.collect_api('')

class KucoinFuturesHandler(KucoinSpotHandler):
    pass
