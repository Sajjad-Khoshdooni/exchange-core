import requests
from celery import shared_task
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from financial.models import Payment, Gateway, FiatWithdrawRequest
from ledger.utils.fields import DONE
import pandas as pd


def send_document():
    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&document={document}'.format(
        token='5780036764:AAGs7ZsYqoIItb0kQO0jCxWikr8CI-07jXM',
        document='https://books.rouzegar.com/ebook/1401/Shah_Siahpooshan.PDF',
        chat_id='73407402',
    )
    resp = requests.post(url, timeout=5)
    return resp.json()


@shared_task(queue='')
def create_daily_transfer():
    gateways = Gateway.objects.all()

    data = {'date': [], 'gateway': [], 'withdraw': [], 'deposit': []}
    for i in range(1, 8):

        date = (timezone.now() - timedelta(days=i)).date()

        for gateway in gateways:
            deposit = Payment.objects.filter(
                created__date=date, payment_request__gateway=gateway, status=DONE,
            ).aggregate(Sum('payment_request__amount'))['payment_request__amount__sum'] or 0

            withdraw = FiatWithdrawRequest.objects.filter(
                created__date=date, status=DONE, withdraw_channel=gateway.name
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            if withdraw or deposit:
                data['date'].append(date)
                data['deposit'].append(deposit)
                data['withdraw'].append(withdraw)
                data['gateway'].append(gateway.name)

    data_frame = pd.DataFrame(data)
    data_frame.to_csv('daily_payment_{}.csv'.format(date), index=False)



