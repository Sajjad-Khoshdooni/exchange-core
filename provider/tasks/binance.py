from celery import shared_task

from accounts.utils.admin import url_to_admin_list
from accounts.utils.telegram import send_system_message
from collector.metrics import set_metric
from ledger.models import Asset
from provider.exchanges import BinanceFuturesHandler, BinanceSpotHandler


@shared_task()
def inject_tether_to_futures():
    details = BinanceFuturesHandler().get_account_details()
    futures_margin_ratio = float(details.get('totalMarginBalance', 0)) / float(details.get('totalInitialMargin', 1e-10))

    if futures_margin_ratio < 2:
        balance_map = BinanceSpotHandler().get_free_dict()
        usdt_amount = min(balance_map[Asset.USDT], 2000)

        if usdt_amount > 1:
            BinanceSpotHandler().transfer('USDT', usdt_amount, 'futures', 1)

        send_system_message(
            message='small margin ratio = %s' % round(futures_margin_ratio, 3),
            link=url_to_admin_list(Asset)
        )

    set_metric('binance_future_margin_ratio', value=futures_margin_ratio)


@shared_task()
def create_transfer_history():
    BinanceSpotHandler().get_withdraw_history()
    BinanceSpotHandler().get_deposit_history()


@shared_task()
def get_binance_wallet():
    BinanceSpotHandler().update_wallet()
    BinanceFuturesHandler().update_wallet()

