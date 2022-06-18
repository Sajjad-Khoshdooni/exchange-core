import math
from decimal import Decimal

from ledger.models import Asset, Network, NetworkAsset
from ledger.utils.price import get_trading_symbol
from market.utils.fix import create_missing_symbols
from provider.exchanges.interface.binance_interface import BinanceSpotHandler, BinanceFuturesHandler


def add_candidate_coins(coins: list):

    order = Asset.objects.order_by('order').last().order

    for coin in coins:
        coin = coin.upper()

        symbol = get_trading_symbol(coin)
        spot = BinanceSpotHandler.get_symbol_data(symbol)

        if not spot or spot['status'] != 'TRADING':
            print('%s not found or stopped trading in interface spot' % coin)
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

        lot_size = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', spot['filters']))[0]
        price_filter = list(filter(lambda f: f['filterType'] == 'PRICE_FILTER', spot['filters']))[0]

        asset.trade_quantity_step = lot_size['stepSize']
        asset.min_trade_quantity = lot_size['minQty']
        asset.max_trade_quantity = lot_size['maxQty']

        asset.price_precision_usdt = -int(math.log10(Decimal(price_filter['tickSize'])))
        asset.price_precision_irt = max(asset.price_precision_usdt - 3, 0)

        if created:
            update_coin_networks(asset)

        asset.save()

    create_missing_symbols()


def update_coin_networks(asset: Asset):
    coin_data = BinanceSpotHandler.get_coin_data(asset.symbol)

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
