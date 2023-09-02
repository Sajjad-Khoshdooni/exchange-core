import math
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from accounts.models import Notification
from ledger.models import AssetAlert, AlertTrigger, Asset
from ledger.utils.external_price import get_external_usdt_prices, USDT, IRT, get_external_price, BUY
from ledger.utils.precision import get_presentation_amount

CACHE_PREFIX = 'asset_alert'

INTERVAL_HOUR_TIME_MAP = {
    AlertTrigger.ONE_HOUR: 1,
    AlertTrigger.THREE_HOURS: 3,
    AlertTrigger.SIX_HOURS: 6,
    AlertTrigger.TWELVE_HOURS: 12,
    AlertTrigger.ONE_DAY: 24
}


def get_current_prices() -> dict:
    coins = list(AssetAlert.objects.distinct('asset').values_list('asset__symbol', flat=True))

    prices = get_external_usdt_prices(coins=coins, side=BUY, apply_otc_spread=True)

    if USDT in prices.keys():
        prices[USDT] = get_external_price(coin=USDT, base_coin=IRT, side=BUY)

    return prices


def send_notifications(asset_alert_list, altered_coins):
    for asset_alert in asset_alert_list:
        base_coin = 'تتر' if asset_alert.asset.symbol != asset_alert.asset.USDT else 'تومان'
        new_price, old_price, interval, is_chanel_changed = altered_coins[asset_alert.asset.symbol]
        percent = math.floor(abs(new_price / old_price - Decimal(1)) * 100)
        change_status = 'افزایش' if new_price > old_price else 'کاهش'
        new_price = get_presentation_amount(new_price, precision=8)

        interval_verbose = AlertTrigger.INTERVAL_VERBOSE_MAP[interval]

        if interval == AlertTrigger.FIVE_MIN:
            title = f'{change_status} ناگهانی قیمت {asset_alert.asset.name_fa}'
        else:
            title = f'{change_status} قیمت {asset_alert.asset.name_fa}'

        if not is_chanel_changed:
            message = (f'قیمت {asset_alert.asset.name_fa} در {interval_verbose} گذشته {percent}'
                       f' درصد {change_status} پیدا کرد و به {new_price} {base_coin} رسید.')
        else:
            message = f'قیمت {asset_alert.asset.name_fa} به {new_price} {base_coin} رسید.'
        Notification.send(
            recipient=asset_alert.user,
            title=title,
            message=message,
        )


def get_altered_coins_by_ratio(past_cycle_prices: dict, current_cycle: dict, current_cycle_count: int,
                               interval: str) -> dict:
    if not past_cycle_prices:
        return {}

    mapping_symbol = {}

    for asset in Asset.live_objects.exclude(symbol=Asset.IRT):
        mapping_symbol[asset.symbol] = asset

    changed_coins = {}

    for coin in past_cycle_prices.keys() & current_cycle.keys():
        asset = mapping_symbol[coin]
        current_price = current_cycle[coin]
        past_price = past_cycle_prices[coin]
        chanel_sensitivity = asset.price_alert_chanel_sensitivity
        current_chanel = current_price // chanel_sensitivity if chanel_sensitivity else None
        past_chanel = current_chanel // chanel_sensitivity if chanel_sensitivity else None
        is_chanel_changed = abs(current_chanel - past_chanel) >= 1 if (
                chanel_sensitivity and interval == AlertTrigger.FIVE_MIN) else False

        change_percent = math.floor(Decimal(current_price / past_price - Decimal(1)) * 100)

        if abs(change_percent) > 5 or (is_chanel_changed and interval == AlertTrigger.FIVE_MIN):
            alert_trigger = AlertTrigger.objects.create(
                asset=asset,
                price=current_price,
                cycle=current_cycle_count,
                change_percent=change_percent,
                chanel=current_chanel,
                interval=interval
            )
            is_sent_recently = AlertTrigger.objects.filter(
                    asset=asset,
                    created__gte=timezone.now() - timedelta(hours=1),
                    is_triggered=True
            ).exists()

            if not is_sent_recently:
                hours = INTERVAL_HOUR_TIME_MAP.get(interval, None)
                is_chanel_new = is_chanel_changed and not AlertTrigger.objects.filter(
                        asset=asset,
                        is_chanel_changed=True,
                        is_triggered=True
                ).last().chanel != current_chanel

                is_interval_price_sent_recently = is_chanel_new or hours and AlertTrigger.objects.filter(
                    asset=asset,
                    is_triggered=True,
                    interval=interval,
                    created__gte=timezone.now() - timedelta(hours=hours)
                ).exists()

                if is_chanel_new or is_interval_price_sent_recently:
                    changed_coins[coin] = [current_price, past_price, interval, True]
                    alert_trigger.is_triggered = True
                    alert_trigger.save(update_fields=['is_triggered'])

    return changed_coins


def get_past_cycle_by_number(cycle_number: int):
    key = CACHE_PREFIX + str(cycle_number)
    return cache.get(key)


@shared_task(queue='notif-manager')
def send_price_notifications():
    total_cycles = 24 * 12

    now = timezone.now()
    current_cycle_count = (now.hour * 60 + now.minute) // 5
    current_cycle_prices = get_current_prices()

    key = CACHE_PREFIX + str(current_cycle_count)
    cache.set(key, current_cycle_prices, 3600 * 24 + 60 * 4)

    past_five_minute_cycle = get_past_cycle_by_number((current_cycle_count - 1) % total_cycles)

    past_hour_cycle = get_past_cycle_by_number((current_cycle_count - 12) % total_cycles)

    past_three_hours_cycle = get_past_cycle_by_number((current_cycle_count - 12 * 3) % total_cycles)

    past_six_hours_cycle = get_past_cycle_by_number((current_cycle_count - 12 * 6) % total_cycles)

    past_twelve_hours_cycle = get_past_cycle_by_number((current_cycle_count - 12 * 12) % total_cycles)

    past_day_cycle = get_past_cycle_by_number((current_cycle_count - 12 * 24) % total_cycles)

    altered_coins = {
        **get_altered_coins_by_ratio(past_five_minute_cycle, current_cycle_prices, current_cycle_count,
                                     interval=AlertTrigger.FIVE_MIN),
        **get_altered_coins_by_ratio(past_hour_cycle, current_cycle_prices, current_cycle_count,
                                     interval=AlertTrigger.ONE_HOUR),
        **get_altered_coins_by_ratio(past_three_hours_cycle, current_cycle_prices, current_cycle_count,
                                     interval=AlertTrigger.SIX_HOURS),
        **get_altered_coins_by_ratio(past_six_hours_cycle, current_cycle_prices, current_cycle_count,
                                     interval=AlertTrigger.SIX_HOURS),
        **get_altered_coins_by_ratio(past_twelve_hours_cycle, current_cycle_prices, current_cycle_count,
                                     interval=AlertTrigger.TWELVE_HOURS),
        **get_altered_coins_by_ratio(past_day_cycle, current_cycle_prices, current_cycle_count,
                                     interval=AlertTrigger.ONE_DAY)
    }

    asset_alert_list = AssetAlert.objects.filter(asset__symbol__in=altered_coins.keys())
    send_notifications(asset_alert_list, altered_coins)
