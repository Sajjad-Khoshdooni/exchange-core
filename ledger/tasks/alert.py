from celery import shared_task
from django.core.cache import cache
from decimal import Decimal

from accounts.models import Notification
from ledger.models.price_alert import PriceTracking
from ledger.utils.external_price import get_external_usdt_prices, USDT, IRT, get_external_price, BUY


def get_current_prices():
    symbols = list(PriceTracking.objects.distinct('asset').values_list('asset__symbol', flat=True))
    symbols_price = {coin: value for coin, value in
                     get_external_usdt_prices(coins=symbols, side=BUY).items() if value and value != Decimal(0.0)}
    if USDT in symbols_price.keys():
        symbols_price[USDT] *= get_external_price(coin=USDT, base_coin=IRT, side=BUY)
    return symbols_price


def send_price_alert_to_user(user, altered_coins):
    tracking_coins = list(PriceTracking.objects.filter(user=user).values_list('asset__symbol', flat=True))
    notifying_coins = {coin for coin in tracking_coins if coin in altered_coins.keys()}
    for coin in notifying_coins:
        Notification.send(
            recipient=user,
            title='تغییر قیمت',
            message=f'تغییر قیمت قابل توجه دارد.! {altered_coins[coin]}'
        )


@shared_task(queue='price_alert')
def send_price_notifications():
    past_cycle_prices = cache.get('coin_prices')
    current_cycle_prices = get_current_prices()
    if not past_cycle_prices:
        cache.set('coin_prices', current_cycle_prices)
        return

    altered_coins = {coin: current_cycle_prices[coin] for coin in past_cycle_prices.keys() & current_cycle_prices.keys()
                     if
                     abs(Decimal(current_cycle_prices[coin] / past_cycle_prices[coin]) - Decimal(1.00)) > Decimal(0.05)
                     }
    selections = PriceTracking.objects.distinct('user')
    for select in selections:
        send_price_alert_to_user(select.user, altered_coins)
    cache.set('coin_prices', current_cycle_prices)
