import datetime
from datetime import timedelta
from secrets import randbelow

import jdatetime
from django.utils import timezone

MINUTES = 60
HOUR = 60 * MINUTES
DAY = 24 * HOUR

PHONE_MAX_LENGTH = 16


def random_number(lower_bound, upper_bound):
    assert lower_bound < upper_bound, 'upper_bound should be greater than lower_bound'

    return lower_bound + randbelow(upper_bound - lower_bound)


def generate_random_code(n: int):
    code = random_number(10 ** (n - 1), 10 ** n)
    return code


def is_email(email: str):
    return '@' in email


def fifteen_minutes_later_datetime():
    now = timezone.now()
    fifteen_minutes = timedelta(seconds=15 * MINUTES)
    return now + fifteen_minutes


def gregorian_to_jalali_date(date: datetime.date):
    return jdatetime.date.fromgregorian(day=date.day, month=date.month, year=date.year)


def gregorian_to_jalali_date_str(date: datetime.date):
    return gregorian_to_jalali_date(date).strftime('%Y/%m/%d')


def gregorian_to_jalali_datetime(d: datetime):
    return jdatetime.datetime.fromgregorian(year=d.year, month=d.month, day=d.day, hour=d.hour, minute=d.minute,
                                            second=d.second)


def gregorian_to_jalali_datetime_str(date: datetime.date):
    return gregorian_to_jalali_date(date).strftime('%Y/%m/%d %H:%M:%S')


def parse_positive_int(inp: str, default: int = None):
    try:
        num = int(inp)

        if num < 0:
            num = default
    except (ValueError, TypeError):
        num = default

    return num
