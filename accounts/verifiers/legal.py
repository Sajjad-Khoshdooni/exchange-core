from datetime import datetime, timedelta, date
from typing import Union

from django.utils import timezone

from accounts.models import User


def is_weekday(d: Union[date, datetime]) -> bool:
    return d.weekday() in (3, 4)


def is_48h_rule_passed(user: User) -> bool:
    if not user.first_fiat_deposit_date or user.withdraw_before_48h_option:
        return True

    elif possible_time_for_withdraw(user=user):
        return False
    else:
        return True


def possible_time_for_withdraw(user: User):
    start = user.first_fiat_deposit_date.astimezone()
    possible_time = start + timedelta(hours=48)
    now = timezone.now()
    if now > possible_time:
        return None
    else:
        return possible_time
