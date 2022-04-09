import logging
from datetime import timedelta
from django.utils import timezone
import jdatetime
from celery import shared_task
from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException
from accounts.models.external_notif import ExternalNotification
from accounts.models import User

logger = logging.getLogger(__name__)


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
