from datetime import timedelta, datetime
from decimal import Decimal

from celery import shared_task
from django.db.models import Sum, F

from accounting.models import PeriodicFetcher, BlocklinkIncome, BlocklinkDustCost
from accounting.requester.blocklink_income import blocklink_income_request
from ledger.models import Transfer, Asset
from ledger.utils.precision import is_zero_by_precision
from ledger.utils.price import get_last_price


def blocklink_income_fetcher(start: datetime, end: datetime):
    result_list = list(Transfer.objects.filter(
        finished_datetime__range=(start, end),
        deposit=False,
    ).values('wallet__asset__symbol', 'network__symbol').annotate(
        total=Sum(F('usdt_value') / (F('amount') + F('fee_amount')) * F('fee_amount'))
    ))

    data_dict = {}

    for item in result_list:
        network_symbol = item['network__symbol']
        coin = item['wallet__asset__symbol']
        total = item['total']
        data_dict[(network_symbol, coin)] = {'total': total}

    resp = blocklink_income_request(start=start, end=end)

    for key, value in resp.items():
        total = 0

        if key in data_dict.keys():
            total = data_dict[key].get('total', 0)

        data_dict[key] = {
            'total': total,
            **value
        }

    for pair, data in data_dict.items():
        network, coin = pair

        network_coin = 'BNB' if network == 'BSC' else network
        price = get_last_price(network_coin + Asset.USDT)

        fee_income = data.get('total', 0)

        fee_amount = Decimal(data.get('fee_amount', 0))
        dust_cost = Decimal(data.get('dust_cost', 0))

        if not is_zero_by_precision(fee_amount + fee_income):
            BlocklinkIncome.objects.get_or_create(
                start=start,
                network=network,
                coin=coin,
                defaults={
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

