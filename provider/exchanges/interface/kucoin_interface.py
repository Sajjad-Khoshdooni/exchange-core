
from decimal import Decimal

from django.conf import settings


from ledger.utils.precision import decimal_to_str
from provider.exchanges.interface.binance_interface import ExchangeHandler, SELL, BUY, MARKET, LIMIT, HOUR
from provider.exchanges.sdk.kucoin_sdk import kucoin_spot_send_signed_request, kucoin_spot_send_public_request


class KucoinSpotHandler(ExchangeHandler):
    MAIN, TRADE, MARGIN, = 'main', 'trade', 'margin',
    order_url = '/api/v1/orders'
    MARKET_TYPE = 'spot'

    _base_api_url = None
    _session = None

    api_path = None
    exchange = None

    def collect_api(self, url: str, method: str = 'POST', data: dict = None, signed: bool = True,
                    cache_timeout: int = None):

        cache_key = None

        # if cache_timeout:
        #     cache_key = get_cache_func_key(self, url, method, data, signed)
        #     result = cache.get(cache_key)
        #
        #     if result is not None:
        #         return result

        result = self._collect_api(url=url, method=method, data=data, signed=signed)

        # if cache_timeout:
        #     cache.set(cache_key, result, cache_timeout)

        return result

    def _collect_api(self, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        # if settings.DEBUG_OR_TESTING:
        #     return {}

        data = data or {}

        if signed:
            return kucoin_spot_send_signed_request(method, url, data=data)
        else:
            return kucoin_spot_send_public_request(url, data=data)

    def get_trading_symbol(self, coin: str) -> str:

        return coin + '-' + 'USDT'

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
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

        return self.collect_api(url=self.order_url, data=data) or {}

    def withdraw(self, coin: str, network: str, address: str, transfer_amount: Decimal, fee_amount: Decimal,
                 address_tag: str = None,
                 client_id: str = None) -> dict:

        amount = decimal_to_str(Decimal(transfer_amount) + Decimal(fee_amount))

        self.transfer(
            asset=coin,
            amount=amount,
            to=self.MAIN,
            client_oid=client_id,
            _from=self.TRADE
        )

        data = {
            'currency': coin,
            'address': address,
            'amount': decimal_to_str(transfer_amount),
            'network': network,
            'memo': address_tag,
            'withdrawOrderId': client_id
        }

        resp = dict()
        resp['id'] = self.collect_api('/api/v1/withdrawals', method='POST', data=data).get('withdrawalId')

        return resp

    def get_account_details(self):
        return self.collect_api(url='/api/v1/accounts', method='GET') or {}

    def get_free_dict(self):
        balances_list = self.get_account_details()
        return {b['currency']: Decimal(b['available']) for b in balances_list if b['type'] == 'trade'}

    def get_all_coins(self):
        return self.collect_api('/api/v1/currencies', method='GET', cache_timeout=HOUR)

    def get_coin_data(self, coin: str):
        return self.collect_api('/api/v2/currencies/{}'.format(coin), method='GET', cache_timeout=HOUR)

    def get_network_info(self, coin: str, network: str):
        chains = self.get_coin_data(coin=coin).get('chains')
        info = list(filter(lambda d: d['chainName'] == network, chains))
        return info

    def get_withdraw_fee(self, coin: str, network: str):
        info = self.get_network_info(coin, network)
        return Decimal(info[0].get('withdrawalMinFee'))

    def transfer(self, asset: str, amount: Decimal, to: str, client_oid: str, _from=TRADE):
        return self.collect_api(
            url='/api/v2/accounts/inner-transfer',
            method='POST',
            data={
                'clientOid': client_oid,
                'currency': asset,
                'from': _from,
                'to': to,
                'amount': amount,
            }
        )

    def get_symbol_data(self, symbol: str):
        data = self.collect_api('/api/v1/symbols', method='GET')
        coin_data = list(filter(lambda d: d['symbol'] == symbol, data))
        if not coin_data:
            return
        return coin_data

    def get_step_size(self, symbol: str) -> Decimal:
        data = self.get_symbol_data(symbol=symbol)
        return data[0].get('quoteIncrement')

    def get_lot_min_quantity(self, symbol: str) ->Decimal:
        data = self.get_symbol_data(symbol=symbol)
        return data[0].get('quoteMinSize')

    def get_withdraw_status(self, withdraw_id: str) -> dict:
        from ledger.models import Transfer
        data = self.collect_api(
            '/api/v1/withdrawals/{}'.format(withdraw_id), 'GET')

        if not data:
            return

        resp = dict()
        resp['txId'] = data.get('walletTxId')
        mapping = {
            'SUCCESS': Transfer.DONE,
            'PROCESSING': Transfer.PROCESSING,
            'FAILURE': Transfer.CANCELED
        }
        resp['status'] = mapping.get(data.get('status'))
        return data


class KucoinFuturesHandler(KucoinSpotHandler):
    order_url = '/api/v1/orders'
    pass

    def _collect_api(self, url: str, method: str = 'POST', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING:
            return {}
        data = data or {}

        if signed:
            return kucoin_spot_send_signed_request(method, url, data=data, futures=True)
        else:
            return kucoin_spot_send_public_request(url, data=data, futures=True)
