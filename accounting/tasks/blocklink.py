from datetime import timedelta, datetime

from celery import shared_task
from django.db.models import Sum, F

from accounting.models import PeriodicFetcher, BlockLinkIncome, BlocklinkDustCost
from accounting.requester.blocklink_income import blocklink_income_request
from ledger.models import Transfer
from ledger.utils.external_price import get_external_price, BUY


def blocklink_income_fetcher(start: datetime, end: datetime):
    resp = blocklink_income_request(start=start, end=end)

    for network, data in resp.items():
        coin = data['coin']
        price = get_external_price(coin=coin, base_coin='USDT', side=BUY, allow_stale=True)
        core_income = Transfer.objects.filter(created__range=(start, end), deposit=False). \
                          aggregate(total=Sum(F('usdt_value') / F('amount') * F('fee_amount')))['total'] or 0

        fee_amount = data['fee_amount']
        dust_cost = data['dust_cost']

        if fee_amount and not BlockLinkIncome.objects.filter(start=start).exists():
            BlockLinkIncome.objects.create(
                start=start,
                network=network,
                coin=coin,
                fee_amount=int(fee_amount),
                usdt_value=price * int(fee_amount),
                core_income=core_income
            )

        if dust_cost:
            BlocklinkDustCost.objects.update(
                network=network,
                coin=coin,
                amount=int(dust_cost),
                usdt_value=int(dust_cost) * price
            )


@shared_task()
def fill_blocklink_incomes():
    PeriodicFetcher.repetitive_fetch(
        name='Blocklink',
        fetcher=blocklink_income_fetcher,
        interval=timedelta(hours=1)
    )

