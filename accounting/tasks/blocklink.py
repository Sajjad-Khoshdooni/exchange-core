from datetime import timedelta, datetime
from decimal import Decimal

from celery import shared_task
from django.db.models import Sum, F

from accounting.models import PeriodicFetcher, BlocklinkIncome, BlocklinkDustCost
from accounting.requester.blocklink_income import blocklink_income_request
from ledger.models import Transfer
from ledger.utils.external_price import get_external_price, BUY


def blocklink_income_fetcher(start: datetime, end: datetime):
    resp = blocklink_income_request(start=start, end=end)

    for network, data in resp.items():
        coin = data['coin']
        price = get_external_price(coin=coin, base_coin='USDT', side=BUY, allow_stale=True)

        fee_income = Transfer.objects.filter(
            created__range=(start, end),
            deposit=False
        ).aggregate(
            total=Sum(F('usdt_value') / F('amount') * F('fee_amount'))
        )['total'] or 0

        fee_amount = Decimal(data['fee_amount'])
        dust_cost = Decimal(data['dust_cost'])

        BlocklinkIncome.objects.get_or_create(
            start=start,
            network=network,
            defaults={
                'coin': coin,
                'real_fee_amount': fee_amount,
                'fee_cost': price * fee_amount,
                'fee_income': fee_income
            }
        )

        BlocklinkDustCost.objects.update_or_create(
            network=network,
            defaults={
                'coin': coin,
                'amount': dust_cost,
                'usdt_value': dust_cost * price
            }
        )


@shared_task()
def fill_blocklink_incomes():
    PeriodicFetcher.repetitive_fetch(
        name='blocklink-pnl',
        fetcher=blocklink_income_fetcher,
        interval=timedelta(hours=1)
    )

