from yekta_metrics import PrometheusClient


prom = PrometheusClient()

METRICS = {
    'binance_total_hedge': prom.gauge('binance_total_hedge', 'interface total hedge', ['currency']),
    'binance_margin_balance': prom.gauge('binance_margin_balance', 'interface margin balance', ['currency']),
    'binance_initial_margin': prom.gauge('binance_initial_margin', 'interface initial margin', ['currency']),
    'binance_maintenance_margin': prom.gauge('binance_maintenance_margin', 'interface maintenance margin', ['currency']),
    'binance_spot_tether': prom.gauge('binance_spot_tether', 'interface spot tether'),
    'binance_future_margin_ratio': prom.gauge('binance_future_margin_ratio', 'interface future margin ratio'),

    'binance_spot_value': prom.gauge('binance_spot_value', 'interface spot value', ['currency']),
    'internal_value': prom.gauge('internal_value', 'internal value', ['currency']),

    'binance_price_updates': prom.counter('binance_price_updates', 'interface price updates'),

    'blockchain_delay': prom.gauge('blockchain_delay', 'blockchain delay', ['network']),
}
