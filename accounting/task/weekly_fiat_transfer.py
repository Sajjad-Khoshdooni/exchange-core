import csv
import os
from datetime import timedelta

import requests
from celery import shared_task
from django.db.models import Sum
from django.utils import timezone
from yekta_config import secret
from yekta_config.config import config

from financial.models import Payment, Gateway, FiatWithdrawRequest
from ledger.models import Asset
from ledger.utils.fields import DONE
from market.models import Trade, Order


def send_accounting_report(file_path: str):
    f = open(file_path, 'rb')
    file_bytes = f.read()
    f.close()

    token = secret('ACCOUNTING_TELEGRAM_TOKEN')
    chat_id = config('ACCOUNTING_TELEGRAM_CHAT_ID')
    document = (f.name, file_bytes)

    url = 'https://api.telegram.org/bot{token}/sendDocument'.format(
        token=token
    )

    resp = requests.post(url, params={'chat_id': chat_id}, files={'document': document}, timeout=10)
    return resp.json()


def add_weekly_payment_dict(weekly_payment_dict: list, date):
    gateways = Gateway.objects.all()

    for gateway in gateways:
        deposit = Payment.objects.filter(
            created__date=date, payment_request__gateway=gateway, status=DONE,
        ).aggregate(Sum('payment_request__amount'))['payment_request__amount__sum'] or 0

        withdraw = FiatWithdrawRequest.objects.filter(
            created__date=date, status=DONE, withdraw_channel=gateway.name
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        if withdraw or deposit:
            data = {}
            data['date'] = date
            data['gateway'] = gateway.name
            data['deposit'] = deposit * 10
            data['withdraw'] = withdraw * 10

            weekly_payment_dict.append(data)

    return weekly_payment_dict


def add_weekly_trade_dict(weekly_trade_dict: list, date):
    sell_trade = Trade.objects.filter(
        created__date=date,
        trade_source__in=(Trade.SYSTEM, Trade.SYSTEM_TAKER, Trade.SYSTEM_MAKER),
        side=Order.SELL,
        symbol__base_asset=Asset.get(Asset.IRT)
    ).aggregate(Sum('irt_value'))['irt_value__sum'] or 0

    buy_trade = Trade.objects.filter(
        created__date=date,
        trade_source__in=(Trade.SYSTEM, Trade.SYSTEM_TAKER, Trade.SYSTEM_MAKER),
        side=Order.BUY,
        symbol__base_asset=Asset.get(Asset.IRT)
    ).aggregate(Sum('irt_value'))['irt_value__sum'] or 0

    if sell_trade or buy_trade:
        dict = {}
        dict['date'] = date
        dict['sell'] = sell_trade * 10
        dict['buy'] = buy_trade * 10
        weekly_trade_dict.append(dict)


@shared_task(queue='accounting')
def create_weekly_accounting_report(days: int = 7):
    weekly_payment_dict = []
    weekly_trade_dict = []

    now = timezone.now()
    for i in range(1, days + 1):
        date = (now - timedelta(days=i)).date()
        add_weekly_payment_dict(weekly_payment_dict, date)
        add_weekly_trade_dict(weekly_trade_dict, date)

    if not os.path.exists('/tmp/accounting'):
        os.makedirs('/tmp/accounting')

    with open('/tmp/accounting/weekly_payment_{}.csv'.format(date), 'w', newline="") as csv_file:
        header = ['date', 'gateway', 'deposit', 'withdraw']
        w = csv.DictWriter(csv_file, fieldnames=header)
        w.writeheader()
        w.writerows(reversed(weekly_payment_dict))

    with open('/tmp/accounting/weekly_trade_{}.csv'.format(date), 'w') as f:
        header = ['date', 'sell', 'buy']
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(reversed('weekly_trade_dict'))

    send_accounting_report(file_path='/tmp/accounting/weekly_payment_{}.csv'.format(date))
    send_accounting_report(file_path='/tmp/accounting/weekly_trade_{}.csv'.format(date))
