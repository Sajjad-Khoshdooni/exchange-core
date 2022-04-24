from datetime import datetime, timedelta

from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from financial.models import FiatWithdrawRequest
from ledger.models import Transfer
from ledger.utils.fields import CANCELED
from ledger.utils.price import get_trading_price_irt, BUY
from ledger.utils.price_manager import PriceManager


MILLION = 10 ** 6

FIAT_WITHDRAW_LIMIT = {
    User.LEVEL1: 0,
    User.LEVEL2: 100 * MILLION,
    User.LEVEL3: 200 * MILLION
}

CRYPTO_WITHDRAW_LIMIT = {
    User.LEVEL1: 200 * MILLION,
    User.LEVEL2: 100 * MILLION,
    User.LEVEL3: 200 * MILLION
}


def get_start_of_day() -> datetime:
    start_of_day = timezone.now().astimezone().date()
    return datetime(start_of_day.year, start_of_day.month, start_of_day.day).astimezone()


def get_fiat_withdraw_irt_value(user: User):
    start_of_day = get_start_of_day()

    fiat_amount = FiatWithdrawRequest.objects.filter(
        bank_account__user=user,
        created__gte=start_of_day
    ).exclude(
        status=CANCELED
    ).aggregate(
        amount=Sum('amount')
    )['amount'] or 0

    return fiat_amount


def get_crypto_withdraw_irt_value(user: User):
    start_of_day = get_start_of_day()

    crypto_withdraws = Transfer.objects.filter(
        deposit=False, hidden=False, is_fee=False,
        wallet__account__user=user,
        created__gte=start_of_day
    ).exclude(
        status=Transfer.CANCELED
    ).values('wallet__asset__symbol').annotate(
        amount=Sum('amount')
    ).values_list('wallet__asset__symbol', 'amount')

    crypto_withdraws = dict(crypto_withdraws)

    crypto_amount = 0

    with PriceManager(coins=list(crypto_withdraws.keys())):
        for symbol, amount in crypto_withdraws.items():
            crypto_amount += get_trading_price_irt(symbol, BUY, raw_price=True) * amount

    return crypto_amount


def user_reached_fiat_withdraw_limit(user: User, irt_value) -> bool:
    return get_fiat_withdraw_irt_value(user) + irt_value > FIAT_WITHDRAW_LIMIT[user.level]


def user_reached_crypto_withdraw_limit(user: User, irt_value) -> bool:
    return get_crypto_withdraw_irt_value(user) + irt_value > CRYPTO_WITHDRAW_LIMIT[user.level]


def time_in_range(start, end, time):
    start = datetime.strptime(start, '%H:%M').time()
    end = datetime.strptime(end, '%H:%M').time()

    return start <= time <= end


def is_holiday(date):
    if date.weekday() == 4:
        return True
    return False


def rial_estimate_receive_time(fiat_withdraw_request: FiatWithdrawRequest):

    fiat_withdraw_request_date = fiat_withdraw_request.created.astimezone()
    fiat_withdraw_request_time = fiat_withdraw_request_date.time()
    receive_time = fiat_withdraw_request_date

    if is_holiday(fiat_withdraw_request_date):

        if time_in_range('00:00', '10:00', fiat_withdraw_request_time):
            receive_time = receive_time.replace(hour=14, minute=00, second=00)

        else:
            receive_time += timedelta(days=1)

            if is_holiday(receive_time):
                receive_time = receive_time.replace(hour=14, minute=00, second=00)
            else:
                receive_time = receive_time.replace(hour=4, minute=30, second=00)

    else:

        if time_in_range('0:30', '10:30', fiat_withdraw_request_time):
            receive_time = receive_time.replace(hour=11, minute=30, second=00)

        elif time_in_range('10:30', '13:23', fiat_withdraw_request_time):
            receive_time = receive_time.replace(hour=14, minute=30, second=00)

        elif time_in_range('13:23', '18:30', fiat_withdraw_request_time):
            receive_time = receive_time.replace(hour=19, minute=30, second=00)

        else:

            receive_time += timedelta(days=1)

            if is_holiday(fiat_withdraw_request_date + timedelta(days=1)):
                receive_time.replace(hour=14, minute=0, second=00)

            else:
                receive_time.replace(hour=4, minute=30, second=00)

    return receive_time
