import re
from datetime import timedelta
from secrets import randbelow
import datetime
import jdatetime

from django.utils import timezone

MINUTES = 60
HOUR = 60 * MINUTES
DAY = 24 * HOUR

PHONE_MAX_LENGTH = 16
EMAIL_MAX_LENGTH = 320


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


def parse_positive_int(inp: str, default: int = None):
    try:
        num = int(inp)

        if num < 0:
            num = default
    except (ValueError, TypeError):
        num = default

    return num
