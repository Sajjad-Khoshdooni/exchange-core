import math
from decimal import Decimal

from ledger.models import Asset, Network, NetworkAsset
from provider.exchanges.binance.interface import BinanceSpotHandler, BinanceFuturesHandler


def add_candidate_coins(coins: list):

    order = Asset.objects.order_by('order').last().order

    for coin in coins:
        coin = coin.upper()

        symbol = coin + 'USDT'
        spot = BinanceSpotHandler.get_symbol_data(symbol)

        if not spot or spot['status'] != 'TRADING':
            print('%s not found or stopped trading in binance spot' % coin)
            continue

        futures = BinanceFuturesHandler.get_symbol_data(symbol)

        asset, created = Asset.objects.get_or_create(symbol=coin)
        asset.hedge_method = Asset.HEDGE_BINANCE_SPOT

        if created:
            order += 1
            asset.order = order

        if not asset.enable:
            asset.candidate = True

        data = spot

        if futures and futures['status'] == 'TRADING':
            asset.hedge_method = Asset.HEDGE_BINANCE_FUTURE
            data = futures

        lot_size = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', data['filters']))[0]
        price_filter = list(filter(lambda f: f['filterType'] == 'PRICE_FILTER', data['filters']))[0]

        asset.trade_quantity_step = lot_size['stepSize']
        asset.min_trade_quantity = lot_size['minQty']
        asset.max_trade_quantity = lot_size['maxQty']

        asset.precision = -int(math.log10(Decimal(lot_size['stepSize'])))
        asset.price_precision_usdt = -int(math.log10(Decimal(price_filter['tickSize'])))
        asset.price_precision_irt = max(asset.price_precision_usdt - 3, 0)

        if created:
            coin_data = BinanceSpotHandler.get_coin_data(coin)

            for n in coin_data['networkList']:
                network, _ = Network.objects.get_or_create(symbol=n['network'], defaults={
                    'name': n['name'],
                    'can_withdraw': False,
                    'can_deposit': False,
                    'address_regex': n['addressRegex'],
                    'min_confirm': n['minConfirm'],
                    'unlock_confirm': n['unLockConfirm'],
                })

                NetworkAsset.objects.get_or_create(
                    asset=asset,
                    network=network,
                    defaults={
                        'withdraw_fee': n['withdrawFee'],
                        'withdraw_min': n['withdrawMin'],
                        'withdraw_max': n['withdrawMax'],
                    }
                )

        asset.save()