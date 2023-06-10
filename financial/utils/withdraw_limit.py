from datetime import datetime

from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from ledger.models import Transfer, Asset
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.fields import CANCELED

MILLION = 10 ** 6

FIAT_WITHDRAW_LIMIT = {
    User.LEVEL1: 0,
    User.LEVEL2: 100 * MILLION,
    User.LEVEL3: 200 * MILLION
}

CRYPTO_WITHDRAW_LIMIT = {
    User.LEVEL1: 0,
    User.LEVEL2: 100 * MILLION,
    User.LEVEL3: 200 * MILLION
}


def get_start_of_day() -> datetime:
    start_of_day = timezone.now().astimezone().date()
    return datetime(start_of_day.year, start_of_day.month, start_of_day.day).astimezone()


def get_fiat_withdraw_irt_value(user: User):
    from financial.models import FiatWithdrawRequest
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
        deposit=False,
        wallet__account__user=user,
        created__gte=start_of_day
    ).exclude(
        status=Transfer.CANCELED
    ).values('wallet__asset__symbol').annotate(
        amount=Sum('amount')
    ).values_list('wallet__asset__symbol', 'amount')

    crypto_withdraws = dict(crypto_withdraws)

    crypto_amount = 0

    for symbol, amount in crypto_withdraws.items():
        price = get_external_price(
            coin=symbol,
            base_coin=Asset.IRT,
            side=BUY,
            allow_stale=True
        )
        crypto_amount += price * amount

    return crypto_amount


def user_reached_fiat_withdraw_limit(user: User, irt_value) -> bool:
    return get_fiat_withdraw_irt_value(user) + irt_value > FIAT_WITHDRAW_LIMIT[user.level]


def user_reached_crypto_withdraw_limit(user: User, irt_value) -> bool:
    ceil = user.custom_crypto_withdraw_ceil or CRYPTO_WITHDRAW_LIMIT[user.level]
    return get_crypto_withdraw_irt_value(user) + irt_value > ceil


def time_in_range(start, end, time):
    start = datetime.strptime(start, '%H:%M').time()
    end = datetime.strptime(end, '%H:%M').time()

    return start <= time < end


def is_holiday(date):
    if date.weekday() == 4:
        return True
    return False
