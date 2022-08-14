import math
from decimal import Decimal

from ledger.models import Asset, Network, NetworkAsset
from market.utils.fix import create_missing_symbols
from provider.exchanges.interface.binance_interface import BinanceSpotHandler, BinanceFuturesHandler
from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler


def add_candidate_coins(coins: list, handler: str):

    handler_mapping = {
        'binance': BinanceSpotHandler,
        'kucoin': KucoinSpotHandler,
    }
    hedger_mapping = {
        'binance': Asset.HEDGE_BINANCE_SPOT,
        'kucoin': Asset.HEDGE_KUCOIN_SPOT
    }

    exchange_handler = handler_mapping.get(handler)()

    order = Asset.objects.order_by('order').last().order

    for coin in coins:
        coin = coin.upper()
        spot_symbol = exchange_handler.get_trading_symbol(coin=coin)

        spot = exchange_handler.get_symbol_data(spot_symbol)

        if not spot or spot.get('status') != 'TRADING':
            print('%s not found or stopped trading in interface spot' % spot_symbol)
            continue

        asset, created = Asset.objects.get_or_create(symbol=coin)

        asset.hedge_method = hedger_mapping[handler]

        if created:
            order += 1
            asset.order = order

        if not asset.enable:
            asset.candidate = True

        if exchange_handler.NAME == BinanceSpotHandler.NAME:
            futures_symbol = BinanceFuturesHandler().get_trading_symbol(coin=coin)
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

        _update_coin_networks(asset=asset, exchange_handler=exchange_handler)

        asset.save()
    create_missing_symbols()


def _update_coin_networks(asset: Asset, exchange_handler):

    coin_data = exchange_handler.get_spot_handler().get_coin_data(asset.symbol)

    for n in coin_data['networkList']:
        network = Network.objects.filter(symbol=n['network'])
        if network:
            network.update(
                address_regex=n['addressRegex'],
                min_confirm=n['minConfirm'],
                unlock_confirm=n['unLockConfirm'],
                kucoin_name=n.get('kucoin_name', '')
            )
            network = network.first()
        else:
            network = Network.objects.create(
                symbol=n['network'],
                name=n['name'],
                kucoin_name=n.get('kucoin_name', ''),
                can_deposit=False,
                can_withdraw=False,
                min_confirm=n['minConfirm'],
                unlock_confirm=n['unLockConfirm'],
                address_regex=n['addressRegex'],
            )

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
        print('alert: have attention to networkasset')
