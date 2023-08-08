from celery import shared_task
from django.core.cache import cache
from decimal import Decimal

from accounts.models import Notification
from ledger.models.price_alert import PriceTracking
from ledger.utils.external_price import get_external_usdt_prices, BUY


@shared_task(queue='price_alert')
def send_price_notifications():
    symbols = list(PriceTracking.objects.distinct('asset').values_list('asset__symbol', flat=True))
    symbols_price = {coin: value for coin, value in
                     get_external_usdt_prices(coins=symbols, side=BUY).items() if value and value != 0}

    past_cycle_prices = cache.get('coin_prices')
    if not past_cycle_prices:
        cache.set('coin_prices', symbols_price)
        return

    common_coins = past_cycle_prices.keys() & symbols_price.keys()
    common_coins_prices = {coin: symbols_price[coin] for coin in common_coins}

    for coin in common_coins:
        if abs(Decimal(symbols_price[coin] / past_cycle_prices[coin]) - Decimal(1.00)) < Decimal(0.05):
            del common_coins_prices[coin]

    users = PriceTracking.objects.distinct('user').only('user', flat=True)
    for user in users:
        tracking_coins = list(PriceTracking.objects.filter(user=user).values_list('asset__symbol', flat=True))
        notifying_coins = {coin for coin in tracking_coins if coin in common_coins_prices.keys()}
        for coin in notifying_coins:
            Notification.send(
                recipient=user,
                title='تغییر قیمت',
                message=f'تغییر قیمت قابل توجه دارد.!{symbols_price[coin]}'
            )

    cache.set('coin_prices', symbols_price)
