import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.models import User, Notification

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
