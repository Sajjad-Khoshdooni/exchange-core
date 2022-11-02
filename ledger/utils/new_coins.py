# import math
# from decimal import Decimal
#
# from ledger.models import Asset, Network, NetworkAsset
# from market.utils.fix import create_symbols_for_asset
# from provider.exchanges.interface.binance_interface import BinanceSpotHandler, BinanceFuturesHandler, ExchangeHandler
# from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler
# from provider.exchanges.interface.mexc_interface import MexcSpotHandler
#
#
# def add_candidate_coins(coins: list, handler: str):
#
#     handler_mapping = {
#         'binance': BinanceSpotHandler,
#         'kucoin': KucoinSpotHandler,
#         'mexc': MexcSpotHandler,
#     }
#     hedger_mapping = {
#         'binance': Asset.HEDGE_BINANCE_SPOT,
#         'kucoin': Asset.HEDGE_KUCOIN_SPOT,
#         'mexc': Asset.HEDGE_MEXC_SPOT,
#     }
#
#     exchange_handler = handler_mapping.get(handler)()
#
#     order = Asset.objects.order_by('order').last().order
#
#     for coin in coins:
#
#         spot_symbol = exchange_handler.get_trading_symbol(coin=coin)
#
#         spot = exchange_handler.get_symbol_data(spot_symbol)
#
#         if not spot or spot.get('status') != 'TRADING':
#             print('%s not found or stopped trading in interface spot' % spot_symbol)
#             continue
#
#         asset, created = Asset.objects.get_or_create(symbol=ExchangeHandler.rename_original_coin_to_internal(coin))
#
#         asset.hedge_method = hedger_mapping[handler]
#
#         if created:
#             order += 1
#             asset.order = order
#
#         if exchange_handler.NAME == BinanceSpotHandler.NAME:
#             futures_symbol = BinanceFuturesHandler().get_trading_symbol(coin=coin)
#             futures = BinanceFuturesHandler().get_symbol_data(futures_symbol)
#             if futures and futures['status'] == 'TRADING':
#                 asset.hedge_method = Asset.HEDGE_BINANCE_FUTURE
#
#         lot_size = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', spot['filters']))[0]
#         price_filter = list(filter(lambda f: f['filterType'] == 'PRICE_FILTER', spot['filters']))[0]
#
#         asset.trade_quantity_step = lot_size['stepSize']
#         asset.min_trade_quantity = Decimal(lot_size['minQty'])
#         asset.max_trade_quantity = Decimal(lot_size['maxQty'])
#
#         asset.price_precision_usdt = -int(math.log10(Decimal(price_filter['tickSize'])))
#         asset.price_precision_irt = max(asset.price_precision_usdt - 3, 0)
#         asset.save()
#         _update_coin_networks(asset=asset, exchange_handler=exchange_handler)
#
#         if not created:
#             print('disable old network assets for {}'.format(coin))
#
#         create_symbols_for_asset(asset)
#
#
# def _update_coin_networks(asset: Asset, exchange_handler):
#
#     coin_data = exchange_handler.get_spot_handler().get_coin_data(asset.symbol)
#
#     for n in coin_data['networkList']:
#         network_symbol = n['network']
#         network = Network.objects.filter(symbol=network_symbol)
#         if network:
#             network.update(
#                 kucoin_name=n.get('kucoin_name', '')
#             )
#             network = network.first()
#         else:
#             network = Network.objects.create(
#                 symbol=network_symbol,
#                 name=n['name'],
#                 kucoin_name=n.get('kucoin_name', ''),
#                 can_deposit=False,
#                 can_withdraw=False,
#                 min_confirm=n['minConfirm'],
#                 unlock_confirm=n.get('unLockConfirm', '0'),
#                 address_regex=n.get('addressRegex', '0')
#             )
#
#         withdraw_integer_multiple = Decimal(n['withdrawIntegerMultiple'])
#
#         if withdraw_integer_multiple == 0:
#             withdraw_integer_multiple = Decimal('1e-9')
#
#         NetworkAsset.objects.get_or_create(
#             asset=asset,
#             network=network,
#             defaults={
#                 'can_withdraw': False,
#                 'withdraw_fee': Decimal(n['withdrawFee']),
#                 'withdraw_min': Decimal(n['withdrawMin']),
#                 'withdraw_max': Decimal(n['withdrawMax']),
#                 'withdraw_precision': -int(math.log10(Decimal(withdraw_integer_multiple)))
#             }
#         )