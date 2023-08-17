from datetime import timedelta, datetime
from decimal import Decimal

from celery import shared_task
from django.db.models import Sum, F

from accounting.models import PeriodicFetcher, BlocklinkIncome, BlocklinkDustCost
from accounting.requester.blocklink_income import blocklink_income_request
from ledger.models import Transfer
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.precision import is_zero_by_precision


def blocklink_income_fetcher(start: datetime, end: datetime):
    resp = blocklink_income_request(start=start, end=end)

    for network, data_list in resp.items():
        network_coin = 'BNB' if network == 'BSC' else network
        price = get_external_price(coin=network_coin, base_coin='USDT', side=BUY, allow_stale=True)

        for data in data_list:
            coin = data['coin']

            fee_income = Transfer.objects.filter(
                finished_datetime__range=(start, end),
                deposit=False,
                network__symbol=network,
                wallet__asset__symbol=coin
            ).aggregate(
                total=Sum(F('usdt_value') / (F('amount') + F('fee_amount')) * F('fee_amount'))
            )['total'] or 0

            fee_amount = Decimal(data['fee_amount'])
            dust_cost = Decimal(data['dust_cost'])

            if not is_zero_by_precision(fee_amount + fee_income):
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

