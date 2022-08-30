from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Union

import pytz
from django.conf import settings
from django.utils import timezone

from ledger.utils.cache import get_cache_func_key, cache
from ledger.utils.precision import decimal_to_str
from ledger.utils.price import get_price
from ledger.utils.price_manager import PriceManager
from provider.exchanges.sdk.binance_sdk import binance_spot_send_signed_request, binance_futures_send_signed_request, \
    binance_futures_send_public_request, binance_spot_send_public_request

MARKET, LIMIT = 'MARKET', 'LIMIT'
SELL, BUY = 'SELL', 'BUY'
GET, POST = 'GET', 'POST'

HOUR = 3600


class ExchangeHandler:
    MARKET_TYPE = ''
    NAME = ''

    @classmethod
    def get_handler(cls, name: str):
        from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler, KucoinFuturesHandler
        from provider.exchanges.interface.mexc_interface import MexcFuturesHandler, MexcSpotHandler
        from ledger.models.asset import Asset

        mapping = {
            Asset.HEDGE_BINANCE_SPOT: BinanceSpotHandler,
            Asset.HEDGE_BINANCE_FUTURE: BinanceFuturesHandler,
            Asset.HEDGE_KUCOIN_SPOT: KucoinSpotHandler,
            Asset.HEDGE_KUCOIN_FUTURE: KucoinFuturesHandler,
            Asset.HEDGE_MEXC_SPOT: MexcSpotHandler,
            Asset.HEDGE_MEXC_FUTURES: MexcFuturesHandler,
        }

        return mapping.get(name, BinanceSpotHandler)()

    @classmethod
    def rename_coin_to_big_coin(cls, coin: str):
        rename_list = {
            'ELON': '1000ELON',
            'BABYDOGE': '1M-BABYDOGE',
            'FLOKI': '1000FLOKI',
            'QUACK': '1M-QUACK',
            'STARL': '1000STARL',
            'SAFEMARS': '1M-SAFEMARS',
        }
        return rename_list.get(coin, coin)

    @classmethod
    def rename_big_coin_to_coin(cls, coin: str):
        rename_list = {
            '1000ELON': 'ELON',
            '1M-BABYDOGE': 'BABYDOGE',
            '1000FLOKI': 'FLOKI',
            '1M-QUACK': 'QUACK',
            '1000STARL': 'STARL',
            '1M-SAFEMARS': 'SAFEMARS'
        }
        return rename_list.get(coin, coin)

    @classmethod
    def get_coin_coefficient(cls, coin: str):
        coin = cls.rename_big_coin_to_coin(coin)
        coin_coefficient = {
            'ELON': Decimal('1000'),
            'BABYDOGE': Decimal('1000000'),
            'FLOKI': Decimal('1000'),
            'QUACK': Decimal('1000000'),
            'STARL': Decimal('1000'),
            'SAFEMARS': Decimal('1000000'),
        }
        return coin_coefficient.get(coin, 1)

    def collect_api(self, url: str, method: str = 'POST', data: dict = None, signed: bool = True,
                    cache_timeout: int = None):
        cache_key = None
        if cache_timeout:
            cache_key = get_cache_func_key(self.__class__, url, method, data, signed)
            result = cache.get(cache_key)
            if result is not None:
                return result

        result = self._collect_api(url=url, method=method, data=data, signed=signed)

        if cache_timeout:
            cache.set(cache_key, result, cache_timeout)

        return result

    def get_min_notional(self):
        return 10

    def _collect_api(self, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        raise NotImplementedError

    def get_trading_symbol(self, symbol: str) -> str:
        raise NotImplementedError

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:
        raise NotImplementedError

    def withdraw(self, coin: str, network, address: str, transfer_amount: Decimal,
                 fee_amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:
        raise NotImplementedError

    def get_account_details(self):
        raise NotImplementedError

    def get_free_dict(self):
        raise NotImplementedError

    def get_all_coins(self):
        raise NotImplementedError

    def get_coin_data(self, coin: str) -> Union[dict, None]:
        raise NotImplementedError

    def get_network_info(self, coin: str, network) -> Union[dict, None]:
        raise NotImplementedError

    def get_withdraw_fee(self, coin: str, network) -> Decimal:
        raise NotImplementedError

    def transfer(self, asset: str, amount: float, market: str, transfer_type: int):
        raise NotImplementedError

    def get_symbol_data(self, symbol: str) -> Union[dict, None]:
        raise NotImplementedError

    def get_step_size(self, symbol: str) -> Decimal:
        raise NotImplementedError

    def get_lot_min_quantity(self, symbol: str) -> Decimal:
        raise NotImplementedError

    def get_withdraw_status(self, withdraw_id: str) -> dict:
        raise NotImplementedError

    def get_spot_handler(self) -> 'ExchangeHandler':
        raise NotImplementedError


class BinanceSpotHandler(ExchangeHandler):
    order_url = '/api/v3/order'
    MARKET_TYPE = 'spot'
    NAME = 'binance'

    def _collect_api(self, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING_OR_STAGING:
            return {}

        data = data or {}

        if signed:
            return binance_spot_send_signed_request(method, url, data)
        else:
            return binance_spot_send_public_request(url, data)

    def get_trading_symbol(self, coin: str) -> str:
        if coin == 'LUNC':
            base = 'BUSD'
        else:
            base = 'USDT'

        if coin == 'BTT':
            coin = 'BTTC'

        return coin + base

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:

        side = side.upper()
        order_type = order_type.upper()

        assert side in (SELL, BUY)
        assert order_type in (MARKET, LIMIT)

        data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': decimal_to_str(amount),
        }

        if client_order_id:
            data['newClientOrderId'] = client_order_id

        return self.collect_api(self.order_url, data=data, method=POST)

    def withdraw(self, coin: str, network, address: str, transfer_amount: Decimal, fee_amount: Decimal,
                 address_tag: str = None, client_id: str = None, memo: str = None) -> dict:

        data = {
            'coin': coin,
            'network': network.symbol,
            'amount': decimal_to_str(Decimal(transfer_amount) + Decimal(fee_amount)),
            'address': address,
            'addressTag': address_tag,
            'withdrawOrderId': client_id
        }
        if memo:
            data['addressTag'] = memo

        return self.collect_api('/sapi/v1/capital/withdraw/apply', method='POST', data=data)

    def get_account_details(self):
        return self.collect_api('/api/v3/account', method='GET') or {}

    def get_free_dict(self):
        balances_list = self.get_account_details()['balances']
        return {b['asset']: Decimal(b['free']) for b in balances_list}

    def get_all_coins(self):
        return self.collect_api('/sapi/v1/capital/config/getall', method='GET', cache_timeout=HOUR)

    def get_coin_data(self, coin: str) -> Union[dict, None]:
        info = list(filter(lambda d: d['coin'] == coin, self.get_all_coins()))

        if not info:
            return

        return info[0]

    def get_network_info(self, coin: str, network) -> Union[dict, None]:
        coin = self.get_coin_data(coin)
        if not coin:
            return

        networks = list(filter(lambda d: d['network'] == network.symbol, coin['networkList']))

        if not networks:
            return

        network = networks[0]

        if not network.get('withdrawMin'):
            network['withdrawMin'] = Decimal(network.get('withdrawIntegerMultiple'))

        return network

    def get_withdraw_fee(self, coin: str, network) -> Decimal:
        info = self.get_network_info(coin, network)
        return Decimal(info['withdrawFee'])

    def transfer(self, asset: str, amount: float, market: str, transfer_type: int):
        return self.collect_api(f'/sapi/v1/{market}/transfer', method='POST', data={
            'asset': asset, 'amount': amount, 'type': transfer_type
        })

    def get_symbol_data(self, symbol: str) -> Union[dict, None]:
        data = self.collect_api('/api/v3/exchangeInfo', data={'symbol': symbol}, signed=False, cache_timeout=HOUR)

        if not data:
            return

        return data['symbols'][0]

    def _get_lot_size_data(self, symbol: str) -> Union[dict, None]:
        data = self.get_symbol_data(symbol)

        if not data:
            return

        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', data['filters']))
        return filters and filters[0]

    def get_step_size(self, symbol: str) -> Decimal:
        lot_size = self._get_lot_size_data(symbol)
        return lot_size and Decimal(lot_size['stepSize'])

    def get_lot_min_quantity(self, symbol: str) -> Decimal:
        lot_size = self._get_lot_size_data(symbol)
        return lot_size and Decimal(lot_size['minQty'])

    def get_withdraw_status(self, withdraw_id: str) -> dict:
        from ledger.models import Transfer
        data = self.collect_api(
            '/sapi/v1/capital/withdraw/history', 'GET',
            data={'withdrawOrderId': withdraw_id}
        )

        if not data:
            return

        data = data[0]

        resp = dict()

        if data['status'] % 2 == 1:
            resp['status'] = Transfer.CANCELED

        elif data['status'] == 6:
            resp['status'] = Transfer.DONE

        else:
            resp['status'] = Transfer.PENDING

        resp['txId'] = data.get('txId')

        return resp

    def _create_transfer_history(self, response: dict, transfer_type: str):
        from provider.models import BinanceTransferHistory
        status_map = {
            BinanceTransferHistory.WITHDRAW: {
                0: BinanceTransferHistory.PENDING,
                1: BinanceTransferHistory.CANCELED,
                2: BinanceTransferHistory.PENDING,
                3: BinanceTransferHistory.CANCELED,
                4: BinanceTransferHistory.PENDING,
                5: BinanceTransferHistory.CANCELED,
                6: BinanceTransferHistory.DONE,
            },
            BinanceTransferHistory.DEPOSIT: {
                0: BinanceTransferHistory.PENDING,
                6: BinanceTransferHistory.PENDING,
                1: BinanceTransferHistory.DONE
            },
        }

        for element in response:
            tx_id = element.get('txId', None)
            binance_id = element.get('id', None)
            address = element['address']
            amount = element['amount']
            coin = element['coin']
            network = element['network']
            status = status_map[transfer_type][element['status']]

            if transfer_type == BinanceTransferHistory.DEPOSIT:
                time = datetime.fromtimestamp(element['insertTime'] // 1000)
                BinanceTransferHistory.objects.update_or_create(
                    tx_id=tx_id,
                    defaults={
                        'binance_id': binance_id,
                        'address': address,
                        'amount': amount,
                        'coin': coin,
                        'date': time.replace(tzinfo=pytz.utc).astimezone(),
                        'network': network,
                        'status': status,
                        'type': transfer_type
                    }
                )
            elif transfer_type == BinanceTransferHistory.WITHDRAW:
                time = element['applyTime']
                BinanceTransferHistory.objects.update_or_create(
                    binance_id=binance_id,
                    defaults={
                        'tx_id': tx_id,
                        'address': address,
                        'amount': amount,
                        'coin': coin,
                        'date': datetime.strptime(time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(),
                        'network': network,
                        'status': status,
                        'type': transfer_type
                    }
                )
            else:
                raise NotImplementedError

    def get_withdraw_history(self, days: int = 5):
        from provider.models import BinanceTransferHistory
        now = timezone.now()
        start_time = int((now - timedelta(days=days)).timestamp() * 1000)

        withdraws = self.collect_api(
            url='/sapi/v1/capital/withdraw/history',
            method=GET,
            data={
                'startTime': start_time
            }
        )

        self._create_transfer_history(response=withdraws, transfer_type=BinanceTransferHistory.WITHDRAW)

    def get_deposit_history(self, days: int = 5):
        from provider.models import BinanceTransferHistory
        now = timezone.now()
        start_time = int((now - timedelta(days=days)).timestamp() * 1000)

        deposits = self.collect_api(
            url='/sapi/v1/capital/deposit/hisrec',
            method=GET,
            data={
                'startTime': start_time
            }
        )

        self._create_transfer_history(response=deposits, transfer_type=BinanceTransferHistory.DEPOSIT)

    def update_wallet(self):
        from provider.models import BinanceWallet
        resp = self.get_account_details()

        wallets = resp['balances']

        for wallet in wallets:
            asset = wallet['asset']
            free = wallet['free']
            locked = wallet['locked']
            with PriceManager(fetch_all=True):
                if asset == '1000SHIB':
                    price = get_price('SHIB', side=BUY.lower()) * 1000
                else:
                    price = get_price(asset, side=BUY.lower())

                if price:
                    usdt_value = Decimal(price) * Decimal(free)
                else:
                    usdt_value = Decimal(0)
            BinanceWallet.objects.update_or_create(
                asset=asset,
                type=BinanceWallet.SPOT,
                defaults={'free': free, 'locked': locked, 'usdt_value': usdt_value}
            )

    def get_spot_handler(self):
        return self


class BinanceFuturesHandler(BinanceSpotHandler):
    order_url = '/fapi/v1/order'
    MARKET_TYPE = 'fut'
    renamed_symbols = {
        'SHIBUSDT': '1000SHIBUSDT'
    }

    def _collect_api(self, url: str, method: str = 'POST', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING_OR_STAGING:
            return {}

        data = data or {}

        if signed:
            return binance_futures_send_signed_request(method, url, data)
        else:
            return binance_futures_send_public_request(url, data)

    def get_account_details(self):
        return self.collect_api('/fapi/v2/account', method='GET')

    def get_order_detail(self, symbol: str, order_id: str):
        return self.collect_api(
            '/fapi/v1/order', method='GET', data={'orderId': order_id, 'symbol': symbol}
        )

    def get_correct_symbol(self, symbol: str) -> str:
        return self.renamed_symbols.get(symbol, symbol)

    def get_symbol_data(self, symbol: str) -> Union[dict, None]:
        if symbol in self.renamed_symbols:
            symbol = self.renamed_symbols[symbol]

        data = self.collect_api('/fapi/v1/exchangeInfo', signed=False, cache_timeout=HOUR)

        if not data:
            return

        data = data['symbols']
        coin_data = list(filter(lambda f: f['symbol'] == symbol, data))

        if not coin_data:
            return

        return coin_data[0]

    def get_lot_size_data(self, symbol: str) -> Union[dict, None]:
        coin_data = self.get_symbol_data(symbol)
        if not coin_data:
            return

        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', coin_data['filters']))

        if filters:
            lot_size = filters[0]

            if symbol in self.renamed_symbols:
                lot_size['stepSize'] = Decimal(lot_size['stepSize']) * 1000
                lot_size['minQty'] = Decimal(lot_size['minQty']) * 1000

            return lot_size

    def get_incomes(self, start_date: datetime, end_date: datetime) -> list:
        return self.collect_api(
            '/fapi/v1/income', method='GET', data={
                # 'incomeType': income_type,
                'startTime': int(start_date.timestamp() * 1000),
                'endTime': int(end_date.timestamp() * 1000),
                'limit': 1000
            }
        )

    def get_position_amount(self, symbol: str) -> Decimal:
        symbol = self.get_correct_symbol(symbol)

        position = list(
            filter(lambda pos: pos['symbol'] == symbol, self.get_account_details()['positions'])
        )[0]

        return Decimal(position.get('positionAmt', 0))

    def update_wallet(self):
        from provider.models import BinanceWallet
        resp = self.get_account_details()

        assets = resp['assets']

        for asset in assets:
            free = (asset['walletBalance'])
            locked = 0

            with PriceManager(fetch_all=True):
                price = get_price(asset['asset'], side=BUY.lower())
                if price:
                    usdt_value = Decimal(price) * Decimal(free)
                else:
                    usdt_value = Decimal(0)

            BinanceWallet.objects.update_or_create(
                asset=asset['asset'],
                type=BinanceWallet.FUTURES,
                defaults={'free': free, 'locked': locked, 'usdt_value': usdt_value},
            )

        positions = resp['positions']

        for position in positions:
            symbol = position['symbol']
            if symbol.endswith('USDT'):
                asset = symbol[:-4]
                free = position['positionAmt']
                locked = 0

                with PriceManager(fetch_all=True):
                    price = get_price(asset, side=BUY.lower())
                    if price:
                        usdt_value = Decimal(price) * Decimal(free)
                    else:
                        usdt_value = Decimal(0)

                BinanceWallet.objects.update_or_create(
                    asset=asset,
                    type=BinanceWallet.FUTURES,
                    defaults={'free': free, 'locked': locked, 'usdt_value': usdt_value},
                )

    def get_spot_handler(self):
        return BinanceSpotHandler()

    def get_free_dict(self):
        raise NotImplementedError

    def withdraw(self, coin: str, network: str, address: str, transfer_amount: Decimal, fee_amount: Decimal,
                 address_tag: str = None, client_id: str = None, memo: str = None) -> dict:
        raise NotImplementedError