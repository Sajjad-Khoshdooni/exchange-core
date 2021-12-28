import logging

from celery import shared_task
from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException
import jdatetime

logger = logging.getLogger(__name__)


message = ''' کد تایید شما در یکتانت: 
{otp}

زمان ارسال: {time} - {date}
مدت اعتبار: ۱۵ دقیقه'''

sender = '100045195000'


@shared_task(queue='sms')
def send_verification_code_by_kavenegar(mobile_number, code, created):
    api_key = settings.KAVEHNEGAR_KEY
    _date, _time = change_datetime_to_jalali(created).split(' ')

    try:
        api = KavenegarAPI(apikey=api_key)
        params = {
            'receptor': mobile_number,
            'message': message.format(otp=code, date=_date, time=_time),
            'sender': sender
        }

        api.sms_send(params)
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
