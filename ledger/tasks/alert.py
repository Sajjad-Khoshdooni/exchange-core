from celery import shared_task

from accounts.models import User
from ledger.models.price_alert import PriceTracking
from ledger.utils.external_price import get_external_usdt_prices, BUY

@shared_task(queue='price_alert')
def send_price_notifications():
    PriceTracking.objects.value()
    coins = list(.values_list('symbol', flat=True))
    prices = get_external_usdt_prices(
        coins=coins,
        side=BUY,
    )


