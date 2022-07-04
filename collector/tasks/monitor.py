from celery import shared_task

from collector.metrics import set_metric
from ledger.models import Asset
from ledger.utils.overview import AssetOverview


USDT_CURRENCY = {'currency': 'USDT'}
IRT_CURRENCY = {'currency': 'IRT'}


@shared_task()
def collect_values():
    overview = AssetOverview()

    set_metric('binance_total_hedge', labels=USDT_CURRENCY, value=overview.get_total_hedge_value())
    set_metric('binance_margin_balance', labels=USDT_CURRENCY, value=overview.total_margin_balance)
    set_metric('binance_initial_margin', labels=USDT_CURRENCY, value=overview.total_initial_margin)
    set_metric('binance_maintenance_margin', labels=USDT_CURRENCY, value=overview.total_maintenance_margin)
    set_metric('binance_spot_tether', value=overview.get_binance_spot_amount(Asset.get(Asset.USDT)))

    set_metric('binance_spot_value', labels=USDT_CURRENCY, value=overview.get_binance_spot_total_value())
    set_metric('internal_value', labels=USDT_CURRENCY, value=overview.get_internal_usdt_value())
    set_metric('fiat_irt', labels=IRT_CURRENCY, value=overview.get_fiat_irt())
    set_metric('total_assets', labels=USDT_CURRENCY, value=overview.get_all_assets_usdt())
    set_metric('exchange_assets', labels=USDT_CURRENCY, value=overview.get_exchange_assets_usdt())
