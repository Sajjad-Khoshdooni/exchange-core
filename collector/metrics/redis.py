from decimal import Decimal

from django.conf import settings
from redis import Redis


prefix_metrics = 'met'
metrics_redis = Redis.from_url(settings.METRICS_CACHE_LOCATION, decode_responses=True)


def set_metric(name: str, labels: dict = None, value: float = 0, timeout: int = 600, incr: bool = False):
    key = f'{prefix_metrics}:{name}'

    if isinstance(value, Decimal):
        value = float(value)

    if labels:
        labels_list = [f'{k}-{v}' for (k, v) in labels.items()]
        key += ':' + ':'.join(labels_list)

    if incr:
        metrics_redis.incr(key, value)
    else:
        metrics_redis.set(key, value, timeout)
