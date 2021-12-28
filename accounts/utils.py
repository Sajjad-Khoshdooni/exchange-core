import re
from datetime import timedelta
from secrets import randbelow

from django.utils import timezone

MINUTES = 60
HOUR = 60 * MINUTES
DAY = 24 * HOUR

PHONE_MAX_LENGTH = 16


def random_number(lower_bound, upper_bound):
    assert lower_bound < upper_bound, 'upper_bound should be greater than lower_bound'

    return lower_bound + randbelow(upper_bound - lower_bound)


def generate_random_code():
    code = random_number(100000, 999999)
    return code


def is_phone(phone: str):
    return re.match(r'(09)(\d){9}', phone)


def is_email(email: str):
    return '@' in email


def fifteen_minutes_later_datetime():
    now = timezone.now()
    fifteen_minutes = timedelta(seconds=15 * MINUTES)
    return now + fifteen_minutes

