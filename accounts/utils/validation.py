import datetime
import logging
from datetime import timedelta
from secrets import randbelow

import jdatetime
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.models.login_activity import LoginActivity
from accounts.utils.ip import get_client_ip

logger = logging.getLogger(__name__)

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
    d = d.astimezone()
    return jdatetime.datetime.fromgregorian(year=d.year, month=d.month, day=d.day, hour=d.hour, minute=d.minute,
                                            second=d.second)


def gregorian_to_jalali_datetime_str(d: datetime):
    return gregorian_to_jalali_datetime(d).strftime('%Y/%m/%d %H:%M:%S')


def parse_positive_int(inp: str, default: int = None):
    try:
        num = int(inp)

        if num < 0:
            num = default
    except (ValueError, TypeError):
        num = default

    return num


def set_login_activity(request, user, is_sign_up : str = False):
    try:
        os = request.user_agent.os.family
        if request.user_agent.os.version_string:
            os += ' ' + request.user_agent.os.version_string

        device = request.user_agent.device.family

        browser = request.user_agent.browser.family

        if request.user_agent.browser.version_string:
            browser += ' ' + request.user_agent.os.version_string

        if request.user_agent.is_mobile:
            device_type = LoginActivity.MOBILE
        elif request.user_agent.is_tablet:
            device_type = LoginActivity.TABLET
        elif request.user_agent.is_pc:
            device_type = LoginActivity.PC
        else:
            device_type = LoginActivity.UNKNOWN

        LoginActivity.objects.create(
            user=user,
            ip=get_client_ip(request),
            user_agent=request.META['HTTP_USER_AGENT'],
            session=Session.objects.get(session_key=request.session.session_key),
            device_type=device_type,
            device=device,
            os=os,
            browser=browser,
            is_sign_up=is_sign_up
        )
    except:
        logger.exception('User login activity dos not saved ')
    return
