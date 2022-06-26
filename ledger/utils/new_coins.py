import math
from decimal import Decimal

from ledger.models import Asset, Network, NetworkAsset
from market.utils.fix import create_missing_symbols
from provider.exchanges.interface.binance_interface import BinanceSpotHandler, BinanceFuturesHandler
from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler


def add_candidate_coins(coins: list, hedger: str):
    hedger = hedger.upper()

    mapping = {
        'BINANCE': BinanceCoins,
        'KUCOIN': KucoinCoins,
    }
    handler = mapping.get(hedger)
    if handler:
        handler = handler()

    else:
        return print('exchange choices are binance and kucoin')

    handler.add_candidate_coins(coins=coins)

    create_missing_symbols()


def update_coin_networks(asset: Asset):

    coin_data = BinanceSpotHandler().get_coin_data(asset.symbol)

    for n in coin_data['networkList']:
        network, _ = Network.objects.get_or_create(symbol=n['network'], defaults={
            'name': n['name'],
            'can_withdraw': False,
            'can_deposit': False,
            'address_regex': n['addressRegex'],
            'min_confirm': n['minConfirm'],
            'unlock_confirm': n['unLockConfirm'],
        })

        withdraw_integer_multiple = Decimal(n['withdrawIntegerMultiple'])

        if withdraw_integer_multiple == 0:
            withdraw_integer_multiple = Decimal('1e-9')

        NetworkAsset.objects.get_or_create(
            asset=asset,
            network=network,
            defaults={
                'withdraw_fee': n['withdrawFee'],
                'withdraw_min': n['withdrawMin'],
                'withdraw_max': n['withdrawMax'],
                'withdraw_precision': -int(math.log10(withdraw_integer_multiple))
            }
        )


class BinanceCoins:

    def add_candidate_coins(self, coins: list):

        order = Asset.objects.order_by('order').last().order

        for coin in coins:
            coin = coin.upper()
            spot_symbol = BinanceSpotHandler().get_trading_symbol(coin=coin)
            futures_symbol = BinanceFuturesHandler().get_trading_symbol(coin=coin)

            spot = BinanceSpotHandler().get_symbol_data(spot_symbol)

            if not spot or spot['status'] != 'TRADING':
                print('%s not found or stopped trading in interface spot' % spot_symbol)

            asset, created = Asset.objects.get_or_create(symbol=coin)

            asset.hedge_method = Asset.HEDGE_BINANCE_SPOT

            if created:
                order += 1
                asset.order = order

            if not asset.enable:
                asset.candidate = True

            futures = BinanceFuturesHandler().get_symbol_data(futures_symbol)

            if futures and futures['status'] == 'TRADING':
                asset.hedge_method = Asset.HEDGE_BINANCE_FUTURE

            lot_size = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', spot['filters']))[0]
            price_filter = list(filter(lambda f: f['filterType'] == 'PRICE_FILTER', spot['filters']))[0]

            asset.trade_quantity_step = lot_size['stepSize']
            asset.min_trade_quantity = lot_size['minQty']
            asset.max_trade_quantity = lot_size['maxQty']

            asset.price_precision_usdt = -int(math.log10(Decimal(price_filter['tickSize'])))
            asset.price_precision_irt = max(asset.price_precision_usdt - 3, 0)

            if created:
                self._update_coin_networks(asset=asset)

            asset.save()

        return

    def _update_coin_networks(self, asset: Asset):

        coin_data = BinanceSpotHandler().get_coin_data(asset.symbol)

        for n in coin_data['networkList']:
            network, _ = Network.objects.get_or_create(symbol=n['network'], defaults={
                'name': n['name'],
                'can_withdraw': False,
                'can_deposit': False,
                'address_regex': n['addressRegex'],
                'min_confirm': n['minConfirm'],
                'unlock_confirm': n['unLockConfirm'],
            })

            withdraw_integer_multiple = Decimal(n['withdrawIntegerMultiple'])

            if withdraw_integer_multiple == 0:
                withdraw_integer_multiple = Decimal('1e-9')

            NetworkAsset.objects.get_or_create(
                asset=asset,
                network=network,
                defaults={
                    'withdraw_fee': n['withdrawFee'],
                    'withdraw_min': n['withdrawMin'],
                    'withdraw_max': n['withdrawMax'],
                    'withdraw_precision': -int(math.log10(withdraw_integer_multiple))
                }
            )


class KucoinCoins:
    def add_candidate_coins(self, coins: list):
        from ledger.models import Asset

        order = Asset.objects.order_by('order').last().order

        for coin in coins:
            coin = coin.upper()
            spot_symbol = KucoinSpotHandler().get_trading_symbol(coin=coin)

            spot = KucoinSpotHandler().get_symbol_data(spot_symbol)[0]

            if not spot or spot['enableTrading'] is not True :
                print('%s not found or stopped trading in interface spot' % spot_symbol)

            asset, created = Asset.objects.get_or_create(symbol=coin)

            asset.hedge_method = Asset.HEDGE_KUCOIN_SPOT

            if created:
                order += 1
                asset.order = order

            if not asset.enable:
                asset.candidate = True

            # lot_size = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', spot['filters']))[0]
            # price_filter = list(filter(lambda f: f['filterType'] == 'PRICE_FILTER', spot['filters']))[0]

            asset.trade_quantity_step = spot['baseIncrement']
            asset.min_trade_quantity = spot['baseMinSize']
            asset.max_trade_quantity = spot['baseMaxSize']

            asset.price_precision_usdt = -int(math.log10(Decimal(spot['priceIncrement'])))
            asset.price_precision_irt = max(asset.price_precision_usdt - 3, 0)

            if created:
                self._update_coin_networks(asset)

            asset.save()

        return

    def _update_coin_networks(self, asset: Asset):

        coin_data = KucoinSpotHandler().get_coin_data(asset.symbol)

        for n in coin_data.get('chains'):
            network, _ = Network.objects.get_or_create(symbol=n.get('chainName'), defaults={
                'name': n.get('chainName'),
                'can_withdraw': False,
                'can_deposit': False,
                'unlock_confirm': n.get('confirms'),
            })

            withdraw_integer_multiple = Decimal(coin_data.get('precision'))

            if withdraw_integer_multiple == 0:
                withdraw_integer_multiple = Decimal('1e-9')

            NetworkAsset.objects.get_or_create(
                asset=asset,
                network=network,
                defaults={
                    'withdraw_fee': n['withdrawalMinFee'],
                    'withdraw_min': n['withdrawalMinSize'],
                    'withdraw_max': '20000000000000',
                    'withdraw_precision': withdraw_integer_multiple
                }
            )
