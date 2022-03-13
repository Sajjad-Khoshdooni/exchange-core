from django.conf import settings
from redis import Redis


prefix_metrics = 'met'
metrics_redis = Redis.from_url(settings.METRICS_CACHE_LOCATION, decode_responses=True)


def set_metric(name: str, labels: dict = None, value: float = 0, timeout: int = 60):
    key = f'{prefix_metrics}:{name}'

    if labels:
        labels_list = [f'{k}-{v}' for (k, v) in labels.items()]
        key += ':' + ':'.join(labels_list)

    metrics_redis.set(key, value, timeout)
