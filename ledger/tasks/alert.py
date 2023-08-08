from celery import shared_task
from django.core.cache import cache
from decimal import Decimal

from accounts.models import Notification
from ledger.models.price_alert import PriceTracking
from ledger.utils.external_price import get_external_usdt_prices, BUY


@shared_task(queue='price_alert')
def send_price_notifications():
    current_cycle_coins = list(PriceTracking.objects.distinct('asset').values_list('asset__symbol', flat=True))
    current_cycle_prices = get_external_usdt_prices(coins=current_cycle_coins, side=BUY)
    current_cycle_prices = {coin: value for coin, value in current_cycle_prices.items() if value and value != 0}
    past_cycle_prices = cache.get('coin_prices')
    if not past_cycle_prices:
        cache.set('coin_prices', current_cycle_prices)
        return
    common_coins = past_cycle_prices.keys() & current_cycle_prices.keys()
    common_coins_prices = {coin: current_cycle_prices[coin] for coin in common_coins}
    for coin in common_coins:
        if abs(Decimal(current_cycle_prices[coin] / past_cycle_prices[coin]) - Decimal(1.00)) < Decimal(0.05):
            del common_coins_prices[coin]
    selections = PriceTracking.objects.distinct('user').only('user')
    for select in selections:
        tracking_coins = list(PriceTracking.objects.filter(user=select.user).values_list('asset__symbol', flat=True))
        notifying_coins = {coin for coin in tracking_coins if coin in common_coins_prices.keys()}
        for coin in notifying_coins:
            Notification.send(
                recipient=select.user,
                title='تغییر قیمت',
                message=f'تغییر قیمت قابل توجه دارد.! {current_cycle_prices[coin]}'
            )
    cache.set('coin_prices', current_cycle_prices)