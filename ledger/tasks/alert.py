from celery import shared_task
from django.core.cache import cache

from accounts.models import Notification
from ledger.models.price_alert import PriceTracking
from ledger.utils.external_price import get_external_usdt_prices, BUY


@shared_task(queue='price_alert')
def send_price_notifications():
    current_cycle_coins = list(PriceTracking.objects.distinct('asset').values_list('coin__symbol'))
    current_cycle_prices = get_external_usdt_prices(coins=current_cycle_coins, side=BUY)
    current_cycle_prices = {coin: value for coin, value in current_cycle_prices.items() if value and value != 0}
    past_cycle_prices = cache.get('coin_prices')
    if not past_cycle_prices:
        cache.set('coin_prices', current_cycle_prices)
    common_coins = past_cycle_prices.keys() & current_cycle_prices.keys()
    for coin in common_coins:
        if abs(current_cycle_prices[coin] / past_cycle_prices[coin] - 1.00) > 0.05:
            del common_coins[coin]
    users = PriceTracking.objects.values_list('user', flat=True)
    for user in users:
        tracking_coins = list(PriceTracking.objects.filter(user=user).values_list('asset__symbol', flat=True))
        prices = {coin: current_cycle_prices[coin] for coin in tracking_coins}
        for price in prices:
            Notification.send(
                recipient=user,
                title='تغییر قیمت',
                message=f'تغییر قیمت قابل توجه دارد.! {price.coin}'
            )
    cache.set('coin_prices', current_cycle_prices)