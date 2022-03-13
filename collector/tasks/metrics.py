from celery import shared_task

from collector.metrics.defs import METRICS
from collector.metrics.redis import metrics_redis, prefix_metrics
import logging

logger = logging.getLogger(__name__)


@shared_task
def collect_metrics():
    metrics = list(metrics_redis.keys(f'{prefix_metrics}_*'))
    pipeline = metrics_redis.pipeline(transaction=False)

    for metric in metrics:
        pipeline.get(metric)

    metrics_values = dict(zip(metrics, pipeline.execute()))

    for key, value in metrics_values.items():
        parts = key.split(':')
        metric_key = parts[1]

        if metric_key not in METRICS:
            logger.log(logging.ERROR, f'metric not found {metric_key}')
            continue

        labels = {l: v for (l, v) in map(lambda s: s.split('-'), parts[2:])}

        gauge = METRICS.pop[metric_key]

        if labels:
            for label in gauge._labelnames:
                if label not in labels:
                    labels[label] = 'null'

            gauge.labels(**labels).set(float(metrics_values[key]))
        else:
            gauge.metrics[metric_key].set(float(value))
