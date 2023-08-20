import math
from decimal import Decimal

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from accounts.models import Notification
from ledger.models.asset_alert import AssetAlert
from ledger.utils.external_price import get_external_usdt_prices, USDT, IRT, get_external_price, BUY


def get_current_prices() -> dict:
    coins = list(AssetAlert.objects.distinct('asset').values_list('asset__symbol', flat=True))

    prices = get_external_usdt_prices(coins=coins, side=BUY, apply_otc_spread=True)

    if USDT in prices.keys():
        prices[USDT] = get_external_price(coin=USDT, base_coin=IRT, side=BUY)

    return prices


def send_notifications(asset_alert_list, altered_coins):
    for asset_alert in asset_alert_list:
        base_coin = 'تتر' if asset_alert.asset.symbol != asset_alert.asset.USDT else 'تومان'
        new_price, old_price = altered_coins[asset_alert.asset.symbol]
        percent = math.floor(abs(new_price / old_price - Decimal(1)) * 100)
        change_status = 'افزایش' if new_price > old_price else 'کاهش'
        Notification.send(
            recipient=asset_alert.user,
            title='تغییر قیمت',
            message=f'قیمت ارزدیجیتال {asset_alert.asset.name_fa} {percent} درصد {change_status} پیدا کرد و به {new_price} {base_coin} رسید.'
        )


def get_altered_coins(past_cycle_prices, current_cycle) -> dict:
    if not past_cycle_prices or current_cycle:
        return {}

    return {coin: [current_cycle[coin], past_cycle_prices[coin]] for coin in
            past_cycle_prices.keys() & current_cycle.keys()
            if
            Decimal(abs(current_cycle[coin] / past_cycle_prices[coin] - Decimal(1))) > Decimal('0.05')
            }


@shared_task(queue='asset_alert')
def send_price_notifications():
    now = timezone.now()
    current_count = math.floor(now.hour * 60 + now.minute / 5)
    current_cycle_prices = get_current_prices()
    cache.set(current_count, current_cycle_prices, 3600 * 25)

    past_five_minute_cycle = cache.get(current_count - 1)
    past_hour_cycle = cache.get(current_count - 12)

    altered_coins = {
        **get_altered_coins(past_five_minute_cycle, current_cycle_prices),
        **get_altered_coins(past_hour_cycle, current_cycle_prices),
    }

    asset_alert_list = AssetAlert.objects.filter(asset__symbol__in=altered_coins.keys())
    send_notifications(asset_alert_list, altered_coins)
