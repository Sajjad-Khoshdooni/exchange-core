from prometheus_client.utils import INF
from yekta_metrics import PrometheusClient


prom = PrometheusClient()

METRICS = {
    'total_hedge': prom.gauge('total_hedge', 'total hedge'),
    'margin_ratio': prom.gauge('margin_ratio', 'margin ratio'),
}
