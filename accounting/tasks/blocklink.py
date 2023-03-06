from datetime import timedelta, datetime

import pytz
from celery import shared_task
from django.db.models import Sum, F

from accounting.models import PeriodicFetcher, ProviderIncome, BlockLinkIncome, DustCost
from accounting.requester.blocklink_income import blocklink_income_request
from ledger.models import Transfer
from ledger.utils.external_price import get_external_price, BUY


@shared_task()
def fill_blocklink_incomes():

    def blocklink_income_fetcher(start: datetime, end: datetime):
        res = blocklink_income_request(start=start, end=end)

        for network, data in res.items():
            coin = data['coin']
            price = get_external_price(coin=coin, base_coin='USDT', side=BUY, allow_stale=True)
            core_income = Transfer.objects.filter(created__range=(start, end), deposit=False).\
            aggregate(total=Sum(F('usdt_value') / F('amount') * F('fee_amount')))['total'] or 0

            BlockLinkIncome.objects.create(
                start=start,
                end=end,
                network=network,
                coin=coin,
                fee_amount=int(data['fee_amount']),
                usdt_value=price * int(data['fee_amount']),
                core_income=core_income
            )

            DustCost.update_dust(
                start=start,
                end=end,
                network=network,
                coin=coin,
                amount=int(data['dust_cost']),
                usdt_value=int(data['dust_cost']) * price
            )

    PeriodicFetcher.repetitive_fetch(
        name='Blocklink',
        fetcher=blocklink_income_fetcher,
        interval=timedelta(hours=1)
    )
