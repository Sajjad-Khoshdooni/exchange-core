import math
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from accounts.models import Notification
from ledger.models import AssetAlert, AlertTrigger
from ledger.utils.external_price import get_external_usdt_prices, USDT, IRT, get_external_price, BUY
from ledger.utils.precision import get_presentation_amount

CACHE_PREFIX = 'asset_alert'


def get_current_prices() -> dict:
    coins = list(AssetAlert.objects.distinct('asset').values_list('asset__symbol', flat=True))

    prices = get_external_usdt_prices(coins=coins, side=BUY, apply_otc_spread=True)

    if USDT in prices.keys():
        prices[USDT] = get_external_price(coin=USDT, base_coin=IRT, side=BUY)

    return prices


def send_notifications(asset_alert_list, altered_coins):
    for asset_alert in asset_alert_list:
        base_coin = 'تتر' if asset_alert.asset.symbol != asset_alert.asset.USDT else 'تومان'
        new_price, old_price, interval = altered_coins[asset_alert.asset.symbol]
        percent = math.floor(abs(new_price / old_price - Decimal(1)) * 100)
        change_status = 'افزایش' if new_price > old_price else 'کاهش'
        new_price = get_presentation_amount(new_price, precision=8)

        interval_verbose = AlertTrigger.INTERVAL_VERBOSE_MAP[interval]

        if interval == AlertTrigger.FIVE_MIN:
            title = f'{change_status} ناگهانی قیمت {asset_alert.asset.name_fa}'
        else:
            title = f'{change_status} قیمت {asset_alert.asset.name_fa}'

        message = f'قیمت {asset_alert.asset.name_fa} در {interval_verbose} گذشته {percent} درصد {change_status} پیدا کرد و به {new_price} {base_coin} رسید.'

        Notification.send(
            recipient=asset_alert.user,
            title=title,
            message=message,
        )


def get_altered_coins(past_cycle_prices: dict, current_cycle: dict, current_cycle_count: int, interval: str) -> dict:
    if not past_cycle_prices:
        return {}

    mapping_symbol = {}

    for asset in Asset.live_objects.exclude(symbol=Asset.IRT):
        mapping_symbol[asset.symbol] = asset

    changed_coins = {}

    for coin in past_cycle_prices.keys() & current_cycle.keys():
        change_percent = math.floor(Decimal(current_cycle[coin] / past_cycle_prices[coin] - Decimal(1)) * 100)
        if abs(change_percent) > 5:
            alert_trigger = AlertTrigger.objects.create(
                asset=mapping_symbol[coin],
                price=current_cycle[coin],
                cycle=current_cycle_count,
                change_percent=change_percent,
                interval=interval
            )
            if not AlertTrigger.objects.filter(
                    asset=mapping_symbol[coin],
                    created__gte=timezone.now() - timedelta(hours=1),
                    is_triggered=True
            ).exists():
                changed_coins[coin] = [current_cycle[coin], past_cycle_prices[coin], interval]
                alert_trigger.is_triggered = True
                alert_trigger.save(update_fields=['is_triggered'])

    return changed_coins


@shared_task(queue='notif-manager')
def send_price_notifications():
    total_cycles = 24 * 12

    now = timezone.now()
    current_cycle_count = (now.hour * 60 + now.minute) // 5
    current_cycle_prices = get_current_prices()

    key = CACHE_PREFIX + str(current_cycle_count)
    cache.set(key, current_cycle_prices, 3600 * 25)

    key = CACHE_PREFIX + str((current_cycle_count - 1) % total_cycles)
    past_five_minute_cycle = cache.get(key)

    key = CACHE_PREFIX + str((current_cycle_count - 12) % total_cycles)
    past_hour_cycle = cache.get(key)

    altered_coins = {
        **get_altered_coins(past_five_minute_cycle, current_cycle_prices, current_cycle_count, interval=AlertTrigger.FIVE_MIN),
        **get_altered_coins(past_hour_cycle, current_cycle_prices, current_cycle_count, interval=AlertTrigger.HOUR),
    }

    asset_alert_list = AssetAlert.objects.filter(asset__symbol__in=altered_coins.keys())
    send_notifications(asset_alert_list, altered_coins)
