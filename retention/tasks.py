import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from accounts.models import User, SmsNotification
from retention.models import Link

logger = logging.getLogger(__name__)


@shared_task()
def send_signup_not_deposited_sms():
    if not settings.RETENTION_ENABLE:
        return

    now = timezone.now()
    start_time, end_time = now - timedelta(hours=2), now - timedelta(minutes=30)

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
