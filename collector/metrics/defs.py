from prometheus_client.utils import INF
from yekta_metrics import PrometheusClient


prom = PrometheusClient()

METRICS = {
    'binance_total_hedge': prom.gauge('binance_total_hedge', 'binance total hedge'),
    'binance_margin_balance': prom.gauge('binance_margin_balance', 'binance margin balance'),
    'binance_initial_margin': prom.gauge('binance_initial_margin', 'binance initial margin'),
    'binance_maintenance_margin': prom.gauge('binance_maintenance_margin', 'binance maintenance margin'),
    'binance_spot_tether': prom.gauge('binance_spot_tether', 'binance spot tether'),
    'binance_future_margin_ratio': prom.gauge('binance_future_margin_ratio', 'binance future margin ratio'),

    'binance_spot_value': prom.gauge('binance_spot_value', 'binance spot value'),
    'internal_value': prom.gauge('internal_value', 'internal value'),

    'binance_price_updates': prom.counter('binance_price_updates', 'binance price updates'),
}
