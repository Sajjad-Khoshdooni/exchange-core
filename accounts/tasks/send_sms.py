import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException
import jdatetime

logger = logging.getLogger(__name__)


@shared_task(queue='sms')
def send_verification_code_by_kavenegar(phone: str, code: str, send_type: str = 'sms'):
    api_key = settings.KAVENEGAR_KEY

    try:
        api = KavenegarAPI(apikey=api_key)
        params = {
            'receptor': phone,
            'template': 'verify',
            'type': send_type,
            'token': code,
        }

        api.verify_lookup(params)
    except (APIException, HTTPException) as e:
        logger.exception("Failed to send verification code")


def change_datetime_to_jalali(gregorian_datetime):
    jalali_datetime = jdatetime.datetime.fromgregorian(
        year=gregorian_datetime.year,
        month=gregorian_datetime.month,
        day=gregorian_datetime.day,
        hour=gregorian_datetime.hour,
        minute=gregorian_datetime.minute,
    )
    return jalali_datetime.strftime('%Y/%m/%d %H:%M')
