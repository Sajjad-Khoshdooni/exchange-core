from django.core.cache import cache
from django.utils import timezone

from ledger.tasks import populate_coins_info


def get_coins_info():
    cached_data = cache.get('coins_info') or {}

    if not cached_data or cached_data['exp'] < timezone.now().timestamp():
        populate_coins_info.delay()

    return cached_data.get('data', [])
