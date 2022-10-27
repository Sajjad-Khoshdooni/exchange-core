import logging

import requests
from celery import shared_task
from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException
from decouple import config
from decouple import config

from accounts.verifiers.finotech import token_cache

logger = logging.getLogger(__name__)


SMS_IR_TOKEN_KEY = 'sms-ir-token'


@shared_task(queue='sms')
def send_message_by_kavenegar(phone: str, template: str, token: str, send_type: str = 'sms'):
    if settings.DEBUG_OR_TESTING:
        return

    if settings.BRAND_EN != 'Raastin':
        template = settings.BRAND_EN.lower() + '-' + template

    api_key = config('KAVENEGAR_KEY')

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
        timeout=15,
        data={
            'UserApiKey': config('SMS_IR_API_KEY'),
            'SecretKey': config('SMS_IR_API_SECRET'),
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

    resp = requests.post(
        url='https://RestfulSms.com/api/UltraFastSend',
        json={
            "ParameterArray": param_array,
            "Mobile":phone,
            "TemplateId": template
        },
        headers={
            'x-sms-ir-secure-token': get_sms_ir_token()
        }
    )

    if not resp.ok:
        return

    data = resp.json()

    if not data['IsSuccessful']:
        logger.error('Failed to send sms via sms.ir', extra={
            'phone': phone,
            'template': template,
            'params': params,
            'data': data
        })

        return

    return data
