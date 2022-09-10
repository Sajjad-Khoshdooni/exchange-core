import requests
from celery import shared_task
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from financial.models import Payment, Gateway, FiatWithdrawRequest
from ledger.utils.fields import DONE
import pandas as pd

from market.models import Trade, Order


def send_document(file_path: str):
    f = open(file_path, 'rb')
    file_bytes = f.read()
    f.close()

    document = (f.name, file_bytes)

    url = 'https://api.telegram.org/bot{token}/sendDocument'.format(
        token='5780036764:AAGs7ZsYqoIItb0kQO0jCxWikr8CI-07jXM'
    )

    params = {
        'chat_id': "-1001640029439"
    }

    files = {
        'document': document
    }

    resp = requests.post(url, params=params, files=files, timeout=5)
    return resp.json()


def edit_payment_daily_dict(daily_payment_dict:dict, date):
    gateways = Gateway.objects.all()

    for gateway in gateways:
        deposit = Payment.objects.filter(
            created__date=date, payment_request__gateway=gateway, status=DONE,
        ).aggregate(Sum('payment_request__amount'))['payment_request__amount__sum'] or 0

        withdraw = FiatWithdrawRequest.objects.filter(
            created__date=date, status=DONE, withdraw_channel=gateway.name
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        if withdraw or deposit:
            daily_payment_dict['date'].append(date)
            daily_payment_dict['deposit'].append(deposit * 10)
            daily_payment_dict['withdraw'].append(withdraw * 10)
            daily_payment_dict['gateway'].append(gateway.name)

    return daily_payment_dict


def edit_daily_trade_dict(daily_trade_dict: dict, date):
    sell_trade = Trade.objects.filter(
        created__date=date,
        trade_source__in=(Trade.SYSTEM, Trade.SYSTEM_TAKER, Trade.SYSTEM_MAKER),
        side=Order.SELL
    ).aggregate(Sum('irt_value'))['irt_value__sum'] or 0

    buy_trade = Trade.objects.filter(
        created__date=date,
        trade_source__in=(Trade.SYSTEM, Trade.SYSTEM_TAKER, Trade.SYSTEM_MAKER),
        side=Order.BUY
    ).aggregate(Sum('irt_value'))['irt_value__sum'] or 0

    if sell_trade or buy_trade:
        daily_trade_dict['date'].append(date)
        daily_trade_dict['sell'].append(sell_trade * 10)
        daily_trade_dict['buy'].append(buy_trade * 10)


@shared_task(queue='')
def create_daily_transfer():

    daily_payment_dict = {'date': [], 'gateway': [], 'withdraw': [], 'deposit': []}
    daily_trade_dict = {'date': [], 'sell': [], 'buy': []}

    for i in range(7, -1, -1):
        date = (timezone.now() - timedelta(days=i)).date()
        edit_payment_daily_dict(daily_payment_dict, date)
        edit_daily_trade_dict(daily_trade_dict, date)

    daily_payment_data_frame = pd.DataFrame(daily_payment_dict)
    daily_payment_data_frame.to_csv('daily_payment_{}.csv'.format(date), index=False)

    daily_trade_data_frame = pd.DataFrame(daily_trade_dict)
    daily_trade_data_frame.to_csv('daily_trade_{}.csv'.format(date), index=False)

    send_document(file_path='daily_payment_{}.csv'.format(date))
    send_document(file_path='daily_trade_{}.csv'.format(date))


#check irt
