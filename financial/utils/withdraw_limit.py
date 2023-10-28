from datetime import datetime

from django.db.models import Sum
from django.utils import timezone

from accounts.models import User, LevelGrants
from ledger.models import Transfer, Asset
from ledger.utils.fields import CANCELED
from ledger.utils.price import get_last_price


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
        price = get_last_price(symbol + Asset.IRT)
        crypto_amount += price * amount

    return crypto_amount


def user_reached_fiat_withdraw_limit(user: User, irt_value) -> bool:
    today_user_fiat_withdraw = get_fiat_withdraw_irt_value(user)
    max_daily_fiat_withdraw = LevelGrants.get_level_grants(user.level).max_daily_fiat_withdraw
    return today_user_fiat_withdraw + irt_value > max_daily_fiat_withdraw


def user_reached_crypto_withdraw_limit(user: User, irt_value) -> bool:
    ceil = user.custom_crypto_withdraw_ceil or LevelGrants.get_level_grants(user.level).max_daily_crypto_withdraw
    return get_crypto_withdraw_irt_value(user) + irt_value > ceil


def time_in_range(start, end, time):
    start = datetime.strptime(start, '%H:%M').time()
    end = datetime.strptime(end, '%H:%M').time()

    return start <= time < end


def is_holiday(date):
    if date.weekday() == 4:
        return True
    return False
