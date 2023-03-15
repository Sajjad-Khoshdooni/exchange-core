import datetime
import json
import logging
from datetime import timedelta
from secrets import randbelow

import jdatetime
import requests
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


def get_ip_data(ip):

    try:
        resp = requests.post(
            url='http://ip-api.com/json/{ip}'.format(ip=ip),
            timeout=1
        )
        return resp.json()

    except:
        return {}


def get_login_activity_from_request(request) -> LoginActivity:
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

        return LoginActivity(
            user_agent=request.META['HTTP_USER_AGENT'],
            device_type=device_type,
            device=device,
            os=os,
            browser=browser,
        )
    except:
        pass


def get_login_activity_from_client_info(client_info: dict) -> LoginActivity:
    return LoginActivity(
        user_agent=json.dumps(client_info),
        device_type=LoginActivity.MOBILE,
        device=client_info.get('device_name', ''),
        os='%s %s' % (client_info.get('system_name', ''), client_info.get('system_version', '')),
        browser=client_info.get('brand', ''),
    )


def set_login_activity(request, user, is_sign_up: bool = False, client_info: dict = None, native_app: bool = False):
    try:
        if client_info:
            login_activity = get_login_activity_from_client_info(client_info)
        else:
            login_activity = get_login_activity_from_request(request)

        ip = get_client_ip(request)
        ip_data = get_ip_data(ip)

        login_activity.user = user
        login_activity.session = Session.objects.filter(session_key=request.session.session_key).first()
        login_activity.is_sign_up = is_sign_up
        login_activity.ip = ip
        login_activity.ip_data = ip_data
        login_activity.city = ip_data.get('city', '')
        login_activity.country = ip_data.get('country', '')
        login_activity.native_app = native_app
        login_activity.save()

    except:
        logger.exception('User login activity dos not saved ')

    return
