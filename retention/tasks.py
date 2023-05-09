import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from accounts.models import User, SmsNotification, Notification
from retention.models import Link

logger = logging.getLogger(__name__)


@shared_task()
def send_signup_not_verified_push():
    group_id = uuid.uuid5(uuid.NAMESPACE_URL, 'signup-not-verified')

    now = timezone.now()
    start_time, end_time = now - timedelta(hours=2), now - timedelta(minutes=15)

    users = User.objects.filter(
        level=User.LEVEL1,
        date_joined__range=[start_time, end_time]
    ).exclude(notification__group_id=group_id)

    for user in users:
        link = 'https://raastin.com/account/verification/basic?utm_source=raastin&utm_medium=push&utm_campaign=30m-verify'

        Notification.objects.create(
            recipient=user,
            group_id=group_id,
            title='هدیه ثبت‌نام در راستین',
            message='با تکمیل احراز هویت هدیه ثبت‌نام خود را دریافت نمایید.',
            link=link,
            level=Notification.INFO,
            push_status=Notification.PUSH_WAITING,
            hidden=True,
        )


@shared_task()
def send_signup_not_deposited_sms():
    if not settings.RETENTION_ENABLE:
        logger.info('ignored due to retention is off')
        return

    now = timezone.now()
    start_time, end_time = now - timedelta(hours=3), now - timedelta(hours=1)

    users = User.objects.filter(
        first_fiat_deposit_date=None,
        first_crypto_deposit_date=None,
        date_joined__range=[start_time, end_time]
    ).exclude(smsnotification__template=SmsNotification.RECENT_SIGNUP_NOT_DEPOSITED)

    for user in users:
        link, _ = Link.objects.get_or_create(user=user, scope=Link.SCOPE_DEPOSIT)

        SmsNotification.objects.get_or_create(
            recipient=user,
            template=SmsNotification.RECENT_SIGNUP_NOT_DEPOSITED,
            params={'link': link.get_link()}
        )
