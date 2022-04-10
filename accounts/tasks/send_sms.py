import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from kavenegar import KavenegarAPI, APIException, HTTPException
from yekta_config import secret
from yekta_config.config import config

from accounts.models import User
from accounts.models.external_notif import ExternalNotification
from accounts.verifiers.finotech import token_cache

logger = logging.getLogger(__name__)


SMS_IR_TOKEN_KEY = 'sms-ir-token'


@shared_task(queue='sms')
def send_message_by_kavenegar(phone: str, template: str, token: str, send_type: str = 'sms'):
    api_key = settings.KAVENEGAR_KEY

    try:
        api = KavenegarAPI(apikey=api_key)
        params = {
            'receptor': phone,
            'template': template,
            'type': send_type,
            'token': token,
        }

        api.verify_lookup(params)
    except (APIException, HTTPException) as e:
        logger.exception("Failed to send sms by kavenegar")


def get_sms_ir_token():

    token = token_cache.get(SMS_IR_TOKEN_KEY)

    if token:
        return token

    resp = requests.post(
        url='https://RestfulSms.com/api/Token',
        data={
            'UserApiKey': config('SMS_IR_API_KEY'),
            'SecretKey': secret('SMS_IR_API_SECRET'),
        }
    )

    if resp.ok:
        resp_data = resp.json()
        token = resp_data['TokenKey']
        expire = 30 * 60

        token_cache.set(SMS_IR_TOKEN_KEY, token, expire)

        return token


@shared_task(queue='sms')
def send_message_by_sms_ir(phone: str, template: str, params: dict):

    param_array = [
        {"Parameter": key, "ParameterValue": value} for (key, value) in params.items()
    ]

    token = get_sms_ir_token()

    resp = requests.post(
        url='https://RestfulSms.com/api/UltraFastSend',
        json={
            "ParameterArray": param_array,
            "Mobile":phone,
            "TemplateId": template
        },
        headers={
            'x-sms-ir-secure-token': token
        }
    )

    data = resp.json()

    if not data['IsSuccessful']:
        logger.error('Failed to send sms via sms.ir', extra={
            'phone': phone,
            'template': template,
            'params': params,
            'data': data
        })

    return data


@shared_task(queue='celery')
def send_level_2_prize_notif():
    three_days_ago = timezone.now() - timedelta(days=3)
    user_ids = ExternalNotification.get_users_sent_sms_notif(ExternalNotification.SCOPE_LEVEL_2_PRIZE)
    users = User.objects.filter(level=User.LEVEL1, date_joined__lte=three_days_ago).exclude(id__in=user_ids)

    for user in users:
        ExternalNotification.send_sms(user, ExternalNotification.SCOPE_LEVEL_2_PRIZE)


@shared_task(queue='celery')
def send_first_fiat_deposit_notif():
    one_day_ago = timezone.now() - timedelta(days=1)
    user_ids = ExternalNotification.get_users_sent_sms_notif(ExternalNotification.SCOPE_FIRST_FIAT_DEPOSIT_PRIZE)
    users = User.objects.filter(
        level=User.LEVEL2, first_fiat_deposit_date=None,
        level_2_verify_datetime__lte=one_day_ago,
    ).exclude(id__in=user_ids)

    for user in users:
        ExternalNotification.send_sms(user, ExternalNotification.SCOPE_FIRST_FIAT_DEPOSIT_PRIZE)
