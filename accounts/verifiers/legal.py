from datetime import datetime, timedelta, date
from typing import Union

from django.utils import timezone

from accounts.models import User


def is_weekday(d: Union[date, datetime]) -> bool:
    return d.weekday() in (3, 4)


def get_working_hour_delta_days(start: datetime, end: datetime) -> float:
    if (end - start).days <= 0:
        return 0

    count = 0

    if not is_weekday(start) and start.hour <= 16:
        count += 1

    if not is_weekday(end) and end.hour >= 14:
        count += 1

    _start = start.date() + timedelta(days=1)
    _end = end.date()

    while _start < _end:
        if not is_weekday(_start):
            count += 1

        _start += timedelta(days=1)

    return count


def is_48h_rule_passed(user: User) -> bool:
    if not user.first_fiat_deposit_date or user.withdraw_before_48h_option:
        return True

    now = timezone.now()

    delta_days = (now - user.first_fiat_deposit_date).days

    if delta_days >= 4:
        return True

    if delta_days < 1:
        return False

    working_days = get_working_hour_delta_days(
        start=user.first_fiat_deposit_date.astimezone(),
        end=now.astimezone()
    )

    return working_days >= 2
