from celery import shared_task
from django.core.cache import cache
from decimal import Decimal
from django.db.models import Q
from accounts.models import Notification
from ledger.models.price_alert import AssetAlert
from ledger.utils.external_price import get_external_usdt_prices, USDT, IRT, get_external_price, BUY


def get_current_prices():
    symbols = list(AssetAlert.objects.distinct('asset').values_list('asset__symbol', flat=True))
    symbols_price = {coin: price for coin, price in
                     get_external_usdt_prices(coins=symbols, side=BUY, apply_otc_spread=True).items() if
                     price and price != Decimal(0)}
    if USDT in symbols_price.keys():
        symbols_price[USDT] = get_external_price(coin=USDT, base_coin=IRT, side=BUY)
    return symbols_price


def send_notifications(selections, altered_coins):
    for select in selections:
        base_coin = 'تتر' if altered_coins[select.asset.symbol] != select.asset.USDT else 'تومان'
        coin = altered_coins[select.asset.symbol]
        percent = abs(altered_coins[coin][0] / altered_coins[coin][1] - Decimal(1))
        change_status = 'افزایش' if altered_coins[coin][0] > altered_coins[coin][1] else 'کاهش'
        new_price = altered_coins[coin][0]
        Notification.send(
            recipient=select.user,
            title='تغییر قیمت',
            message=f'قیمت ارزدیجیتال {select.asset.name_fa} {percent} درصد {change_status} پیدا کرد و به {new_price} {base_coin} رسید.'
        )


def get_altered_coins(past_cycle_prices, current_cycle):
    return {coin: [current_cycle[coin], past_cycle_prices[coin]] for coin in
            past_cycle_prices.keys() & current_cycle.keys()
            if
            abs(Decimal(current_cycle[coin] / past_cycle_prices[coin]) - Decimal(
                1.00)) > Decimal(0.05)
            }


@shared_task(queue='price_alert')
def send_price_notifications():
    past_data = cache.get('coin_prices')
    current_cycle = get_current_prices()
    if not past_data:
        cache.set('coin_prices', {'initial': current_cycle, 'past': current_cycle, 'count': 0}, 60 * 10)
        return
    initial_cycle = past_data['initial']
    past_cycle = past_data['past']
    count = past_cycle['count']

    altered_coins = get_altered_coins(past_cycle, current_cycle)
    if count % 12 == 0:
        altered_coins = get_altered_coins(initial_cycle, current_cycle)
    selections = AssetAlert.objects.filter(Q(asset__symbol__in=altered_coins.keys()))
    send_notifications(selections, altered_coins)
    cache.set('coin_prices', {'initial': current_cycle if count % 12 == 0 else initial_cycle, 'past': current_cycle,
                              'count': count + 1})
