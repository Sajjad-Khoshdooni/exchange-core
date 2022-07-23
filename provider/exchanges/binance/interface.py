from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union

from django.conf import settings

from ledger.utils.cache import get_cache_func_key, cache
from ledger.utils.precision import decimal_to_str
from provider.exchanges.binance.sdk import spot_send_signed_request, futures_send_signed_request, \
    spot_send_public_request, futures_send_public_request


BINANCE = 'binance'

MARKET, LIMIT = 'MARKET', 'LIMIT'
SELL, BUY = 'SELL', 'BUY'
GET, POST = 'GET', 'POST'

HOUR = 3600

SPOT, FUTURES = 'spot', 'futures'


class BinanceSpotHandler:
    order_url = '/api/v3/order'

    @classmethod
    def collect_api(cls, url: str, method: str = 'POST', data: dict = None, signed: bool = True,
                    cache_timeout: int = None):
        cache_key = None

        if cache_timeout:
            cache_key = get_cache_func_key(cls, url, method, data, signed)
            result = cache.get(cache_key)

            if result is not None:
                return result

        result = cls._collect_api(url=url, method=method, data=data, signed=signed)

        if cache_timeout:
            cache.set(cache_key, result, cache_timeout)

        return result

    @classmethod
    def _collect_api(cls, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING:
            return {}

        data = data or {}

        if signed:
            return spot_send_signed_request(method, url, data)
        else:
            return spot_send_public_request(url, data)

    @classmethod
    def place_order(cls, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
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

        return cls.collect_api(cls.order_url, data=data, method=POST)

    @classmethod
    def withdraw(cls, coin: str, network: str, address: str, amount: Decimal, address_tag: str = None,
                 client_id: str = None, memo: str = None) -> dict:
        data = {
            'coin': coin,
            'network': network,
            'amount': decimal_to_str(amount),
            'address': address,
            'addressTag': address_tag,
            'withdrawOrderId': client_id
        }
        if memo:
            data['addressTag'] = memo

        return cls.collect_api('/sapi/v1/capital/withdraw/apply', method='POST', data=data)

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/api/v3/account', method='GET') or {}

    @classmethod
    def get_free_dict(cls):
        balances_list = BinanceSpotHandler.get_account_details()['balances']
        return {b['asset']: Decimal(b['free']) for b in balances_list}

    @classmethod
    def get_all_coins(cls):
        return cls.collect_api('/sapi/v1/capital/config/getall', method='GET', cache_timeout=HOUR)

    @classmethod
    def get_coin_data(cls, coin: str) -> Union[dict, None]:
        info = list(filter(lambda d: d['coin'] == coin, cls.get_all_coins()))

        if not info:
            return

        return info[0]

    @classmethod
    def get_network_info(cls, coin: str, network: str) -> Union[dict, None]:
        coin = cls.get_coin_data(coin)
        if not coin:
            return

        networks = list(filter(lambda d: d['network'] == network, coin['networkList']))

        if networks:
            return networks[0]

    @classmethod
    def get_withdraw_fee(cls, coin: str, network: str) -> Decimal:
        info = cls.get_network_info(coin, network)
        return Decimal(info['withdrawFee'])

    @classmethod
    def transfer(cls, asset: str, amount: float, market: str, transfer_type: int):
        return cls.collect_api(f'/sapi/v1/{market}/transfer', method='POST', data={
            'asset': asset, 'amount': amount, 'type': transfer_type
        })

    @classmethod
    def get_symbol_data(cls, symbol: str) -> Union[dict, None]:
        data = cls.collect_api('/api/v3/exchangeInfo', data={'symbol': symbol}, signed=False, cache_timeout=HOUR)

        if not data:
            return

        return data['symbols'][0]

    @classmethod
    def get_lot_size_data(cls, symbol: str) -> Union[dict, None]:
        data = cls.get_symbol_data(symbol)

        if not data:
            return

        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', data['filters']))
        return filters and filters[0]

    @classmethod
    def get_step_size(cls, symbol: str) -> Decimal:
        lot_size = cls.get_lot_size_data(symbol)
        return lot_size and Decimal(lot_size['stepSize'])

    @classmethod
    def get_lot_min_quantity(cls, symbol: str) -> Decimal:
        lot_size = cls.get_lot_size_data(symbol)
        return lot_size and Decimal(lot_size['minQty'])

    @classmethod
    def _create_transfer_history(cls, response: dict, transfer_type: str):
        from provider.models import BinanceWithdrawDepositHistory
        status_map = {
            BinanceWithdrawDepositHistory.WITHDRAW : {
                0: BinanceWithdrawDepositHistory.PENDING,
                1: BinanceWithdrawDepositHistory.CANCELED,
                2: BinanceWithdrawDepositHistory.PENDING,
                3: BinanceWithdrawDepositHistory.CANCELED,
                4: BinanceWithdrawDepositHistory.PENDING,
                5: BinanceWithdrawDepositHistory.CANCELED,
                6: BinanceWithdrawDepositHistory.DONE,
            },
            BinanceWithdrawDepositHistory.DEPOSIT: {
                0: BinanceWithdrawDepositHistory.PENDING,
                6: BinanceWithdrawDepositHistory.PENDING,
                1: BinanceWithdrawDepositHistory.DONE
            },
        }

        for element in response:
            tx_id = element['txId']
            address = element['address']
            amount = element['amount']
            coin = element['coin']
            network = element['network']
            status = status_map[transfer_type][element['status']]
            withdraw_deposit = BinanceWithdrawDepositHistory.objects.filter(tx_id=tx_id)
            if withdraw_deposit:
                BinanceWithdrawDepositHistory.objects.update(status=status)
            else:
                if transfer_type == BinanceWithdrawDepositHistory.DEPOSIT:
                    time = datetime.fromtimestamp(element['insertTime']//1000)
                else:
                    time = element['applyTime']
                BinanceWithdrawDepositHistory.objects.create(
                    tx_id=tx_id,
                    address=address,
                    amount=amount,
                    coin=coin,
                    date=time,
                    network=network,
                    status=status,
                    type=transfer_type,
                )

    @classmethod
    def get_withdraw_history(cls):
        from provider.models import BinanceWithdrawDepositHistory
        now = datetime.now()
        five_days_ago_time_timestamp = datetime.timestamp(now - timedelta(days=5))

        withdraws = cls.collect_api(
            url='/sapi/v1/capital/withdraw/history',
            method=GET,
            data={
                'startTime': five_days_ago_time_timestamp
            }
        )

        cls._create_transfer_history(response=withdraws, transfer_type=BinanceWithdrawDepositHistory.WITHDRAW)

    @classmethod
    def get_deposit_history(cls):
        from provider.models import BinanceWithdrawDepositHistory
        now = datetime.now()
        five_days_ago_time_timestamp = datetime.timestamp(now - timedelta(days=5))

        deposits = cls.collect_api(
            url='/sapi/v1/capital/deposit/hisrec',
            method=GET,
            data={
                'startTime': five_days_ago_time_timestamp
            })

        cls._create_transfer_history(response=deposits, transfer_type=BinanceWithdrawDepositHistory.DEPOSIT)

    @classmethod
    def _get_spot_and_futures_wallet_handler(cls, wallet_type):
        from provider.models import BinanceWallet
        resp = cls.collect_api(
            url='/sapi/v1/accountSnapshot',
            method=GET,
            data={
                'type': wallet_type
            }
        )
        wallets = resp['snapshotVos'][0]['data']['balances']

        for wallet in wallets:
            asset = wallet['asset']
            free = wallet['free']
            locked = wallet['locked']
            binance_wallet = BinanceWallet.objects.filter(asset=asset)

            if binance_wallet:
                binance_wallet.update(free=free, locked=locked)
            else:
                BinanceWallet.objects.create(asset=asset, free=free, locked=locked, type=wallet_type)

    @classmethod
    def get_spot_wallets(cls):
        from provider.models import BinanceWallet

        cls._get_spot_and_futures_wallet_handler(BinanceWallet.SPOT)


class BinanceFuturesHandler(BinanceSpotHandler):
    order_url = '/fapi/v1/order'

    renamed_symbols = {
        'SHIBUSDT': '1000SHIBUSDT'
    }

    @classmethod
    def _collect_api(cls, url: str, method: str = 'POST', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING:
            return {}

        data = data or {}

        if signed:
            return futures_send_signed_request(method, url, data)
        else:
            return futures_send_public_request(url, data)

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/fapi/v2/account', method='GET')

    @classmethod
    def get_order_detail(cls, symbol: str, order_id: str):
        return cls.collect_api(
            '/fapi/v1/order', method='GET', data={'orderId': order_id, 'symbol': symbol}
        )

    @classmethod
    def get_symbol_data(cls, symbol: str) -> Union[dict, None]:
        if symbol in cls.renamed_symbols:
            symbol = cls.renamed_symbols[symbol]

        data = cls.collect_api('/fapi/v1/exchangeInfo', signed=False, cache_timeout=HOUR)

        if not data:
            return

        data = data['symbols']
        coin_data = list(filter(lambda f: f['symbol'] == symbol, data))

        if not coin_data:
            return

        return coin_data[0]

    @classmethod
    def get_lot_size_data(cls, symbol: str) -> Union[dict, None]:
        coin_data = cls.get_symbol_data(symbol)
        if not coin_data:
            return

        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', coin_data['filters']))

        if filters:
            lot_size = filters[0]

            if symbol in cls.renamed_symbols:
                lot_size['stepSize'] = Decimal(lot_size['stepSize']) * 1000
                lot_size['minQty'] = Decimal(lot_size['minQty']) * 1000

            return lot_size

    @classmethod
    def get_incomes(cls, start_date: datetime, end_date: datetime) -> list:
        return cls.collect_api(
            '/fapi/v1/income', method='GET', data={
                # 'incomeType': income_type,
                'startTime': int(start_date.timestamp() * 1000),
                'endTime': int(end_date.timestamp() * 1000),
                'limit': 1000
            }
        )

    @classmethod
    def get_futures_wallets(cls):
        from provider.models import BinanceWallet
        cls._get_spot_and_futures_wallet_handler(BinanceWallet.FUTURES)