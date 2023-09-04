import math
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from accounts.models import Notification, User
from ledger.models import CoinCategory, AssetAlert, BulkAssetAlert, AlertTrigger, Asset
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

INTERVAL_CHANGE_PERCENT_SENSITIVITY_MAP = {
    AlertTrigger.FIVE_MIN: 5,
    AlertTrigger.ONE_HOUR: 5,
    AlertTrigger.THREE_HOURS: 10,
    AlertTrigger.SIX_HOURS: 10,
    AlertTrigger.TWELVE_HOURS: 20,
    AlertTrigger.ONE_DAY: 20
}


@dataclass
class AlertData:
    user: User
    asset: Asset

    def __hash__(self):
        return hash((self.user, self.asset))

    def __eq__(self, other):
        if not isinstance(other, AlertData):
            return NotImplemented
        return (self.user, self.asset) == (other.user, other.asset)


def get_current_prices() -> dict:
    coins = list(Asset.objects.values_list('symbol', flat=True))

    prices = get_external_usdt_prices(coins=coins, side=BUY)

    if USDT in prices.keys():
        prices[USDT] = get_external_price(coin=USDT, base_coin=IRT, side=BUY)

    return prices


def send_notifications(asset_alerts, altered_coins):
    for alert in asset_alerts:
        base_coin = 'تتر' if alert.asset.symbol != alert.asset.USDT else 'تومان'
        new_price, old_price, interval, is_chanel_changed = altered_coins[alert.asset.symbol]
        percent = math.floor(abs(new_price / old_price - Decimal(1)) * 100)
        change_status = 'افزایش' if new_price > old_price else 'کاهش'
        new_price = get_presentation_amount(new_price, precision=8)

        interval_verbose = AlertTrigger.INTERVAL_VERBOSE_MAP[interval]

        if interval == AlertTrigger.FIVE_MIN and not is_chanel_changed:
            title = f'{change_status} ناگهانی قیمت {alert.asset.name_fa}'
        else:
            title = f'{change_status} قیمت {alert.asset.name_fa}'

        if not is_chanel_changed:
            message = (f'قیمت {alert.asset.name_fa} در {interval_verbose} گذشته {percent}'
                       f' درصد {change_status} پیدا کرد و به {new_price} {base_coin} رسید.')
        else:
            message = f'قیمت {alert.asset.name_fa} به {new_price} {base_coin} رسید.'
        Notification.send(
            recipient=alert.user,
            title=title,
            message=message,
            link=f'/price/{alert.asset.name}'
        )


def get_altered_coins(past_cycle_prices: dict, current_cycle: dict, current_cycle_count: int,
                      interval: str) -> dict:
    if not past_cycle_prices:
        return {}

    mapping_symbol = {}

    for asset in Asset.live_objects.exclude(symbol=Asset.IRT):
        mapping_symbol[asset.symbol] = asset

    changed_coins = {}

    for coin in past_cycle_prices.keys() & current_cycle.keys():
        asset = mapping_symbol.get(coin, None)
        if not asset:
            continue
        current_price = current_cycle[coin]
        past_price = past_cycle_prices[coin]
        chanel_sensitivity = asset.price_alert_chanel_sensitivity
        current_chanel = current_price // chanel_sensitivity if chanel_sensitivity else None
        past_chanel = past_price // chanel_sensitivity if chanel_sensitivity else None
        is_chanel_changed = abs(current_chanel - past_chanel) >= 1 if (
                chanel_sensitivity and interval == AlertTrigger.FIVE_MIN) else False

        change_percent = math.floor(Decimal(current_price / past_price - Decimal(1)) * 100)
        if abs(change_percent) > INTERVAL_CHANGE_PERCENT_SENSITIVITY_MAP[interval] or is_chanel_changed:
            alert_trigger = AlertTrigger.objects.create(
                asset=asset,
                price=current_price,
                cycle=current_cycle_count,
                change_percent=change_percent,
                chanel=current_chanel,
                is_chanel_changed=is_chanel_changed,
                interval=interval
            )
            is_sent_recently = AlertTrigger.objects.filter(
                asset=asset,
                created__gte=timezone.now() - timedelta(hours=1),
                is_triggered=True
            ).exists()
            if not is_sent_recently:
                hours = INTERVAL_HOUR_TIME_MAP.get(interval, None)
                last_chanel_triggered_alert = AlertTrigger.objects.filter(
                    asset=asset,
                    is_chanel_changed=True,
                    is_triggered=True
                ).last()
                is_chanel_new = is_chanel_changed and not (
                            last_chanel_triggered_alert and last_chanel_triggered_alert.chanel == current_chanel)

                is_interval_price_sent_recently = None
                if hours and not is_chanel_new:
                    is_interval_price_sent_recently = AlertTrigger.objects.filter(
                        asset=asset,
                        is_triggered=True,
                        interval=interval,
                        created__gte=timezone.now() - timedelta(hours=hours)
                    ).exists()

                if is_chanel_new or is_interval_price_sent_recently == False:
                    changed_coins[coin] = [current_price, past_price, interval, is_chanel_new]
                    alert_trigger.is_triggered = True
                    alert_trigger.save(update_fields=['is_triggered'])

    return changed_coins


def get_past_cycle_by_number(cycle_number: int):
    key = CACHE_PREFIX + str(cycle_number)
    return cache.get(key)


def get_asset_alert_list(altered_coins: dict) -> set:
    asset_alerts = set()
    all_assets = Asset.live_objects.filter(symbol__in=altered_coins.keys())
    all_categories = CoinCategory.objects.all()
    category_map = {}
    for category in all_categories:
        category_map[category] = category.coins.filter(symbol__in=altered_coins.keys())
    for asset_alert in AssetAlert.objects.filter(asset__symbol__in=altered_coins.keys()):
        asset_alerts.add(
            AlertData(
                user=asset_alert.user,
                asset=asset_alert.asset,
            )
        )
    for bulk_asset_alert in BulkAssetAlert.objects.all():
        subscription_type = bulk_asset_alert.subscription_type
        if subscription_type == BulkAssetAlert.CATEGORY_ALL_COINS:
            subscribed_coins = all_assets
        elif subscription_type == BulkAssetAlert.CATEGORY_MY_ASSETS:
            subscribed_coins = Asset.objects.filter(
                symbol__in=altered_coins.keys(),
                wallet__account=bulk_asset_alert.user.get_account(),
                wallet__balance__gt=0
            )
        else:
            subscribed_coins = category_map[bulk_asset_alert.coin_category]
        for asset in subscribed_coins:
            asset_alerts.add(AlertData(
                user=bulk_asset_alert.user,
                asset=asset
            ))
    return asset_alerts


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

    past_day_cycle = get_past_cycle_by_number((current_cycle_count + 2) % total_cycles)

    altered_coins = {
        **get_altered_coins(past_five_minute_cycle, current_cycle_prices, current_cycle_count,
                            interval=AlertTrigger.FIVE_MIN),
        **get_altered_coins(past_hour_cycle, current_cycle_prices, current_cycle_count,
                            interval=AlertTrigger.ONE_HOUR),
        **get_altered_coins(past_three_hours_cycle, current_cycle_prices, current_cycle_count,
                            interval=AlertTrigger.THREE_HOURS),
        **get_altered_coins(past_six_hours_cycle, current_cycle_prices, current_cycle_count,
                            interval=AlertTrigger.SIX_HOURS),
        **get_altered_coins(past_twelve_hours_cycle, current_cycle_prices, current_cycle_count,
                            interval=AlertTrigger.TWELVE_HOURS),
        **get_altered_coins(past_day_cycle, current_cycle_prices, current_cycle_count,
                            interval=AlertTrigger.ONE_DAY),
    }

    asset_alert_list = get_asset_alert_list(altered_coins)

    send_notifications(asset_alert_list, altered_coins)
