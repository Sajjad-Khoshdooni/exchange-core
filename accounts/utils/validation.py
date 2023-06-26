import datetime
import json
import logging
from datetime import timedelta
from secrets import randbelow

import jdatetime
import requests
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.models.refresh_token import RefreshToken
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


def get_login_user_agent_data_from_request(request) -> dict:
    os = request.user_agent.os.family
    os_version = request.user_agent.os.version_string
    if os_version:
        os += ' ' + os_version

    device = request.user_agent.device.family

    browser = request.user_agent.browser.family
    browser_version = request.user_agent.browser.version_string

    if browser_version:
        browser += ' ' + browser_version

    if request.user_agent.is_mobile:
        device_type = LoginActivity.MOBILE
    elif request.user_agent.is_tablet:
        device_type = LoginActivity.TABLET
    elif request.user_agent.is_pc:
        device_type = LoginActivity.PC
    else:
        device_type = LoginActivity.UNKNOWN

    return {
        'user_agent': request.META['HTTP_USER_AGENT'],
        'device_type': device_type,
        'device': device,
        'os': os,
        'browser': browser
    }


def get_login_user_agent_data_from_client_info(client_info: dict) -> dict:
    return {
        'user_agent': json.dumps(client_info),
        'device_type': LoginActivity.MOBILE,
        'device': client_info.get('device_name', ''),
        'os': '%s %s' % (client_info.get('system_name', ''), client_info.get('system_version', '')),
        'browser': client_info.get('brand', ''),
    }


def get_refresh_token_from_request(request):
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.startswith('Bearer ') and auth_header.split(' ')[1]
    return token


def set_login_activity(request, user, is_sign_up: bool = False, client_info: dict = None, native_app: bool = False):
    session = Session.objects.filter(session_key=request.session.session_key).first()

    if not session:
        return

    if client_info:
        user_agent_data = get_login_user_agent_data_from_client_info(client_info)
    else:
        user_agent_data = get_login_user_agent_data_from_request(request)

    ip = get_client_ip(request)
    ip_data = get_ip_data(ip)

    refresh_token = get_refresh_token_from_request(request)
    refresh_token_model = None
    if refresh_token:
        refresh_token_model = RefreshToken.objects.get_or_create(token=refresh_token)

    LoginActivity.objects.get_or_create(
        session=session,

        defaults={
            **user_agent_data,
            'user': user,
            'is_sign_up': is_sign_up,
            'ip': ip,
            'ip_data': ip_data,
            'city': ip_data.get('city', ''),
            'country': ip_data.get('country', ''),
            'native_app': native_app,
            'refresh_token': refresh_token_model
        }
    )
