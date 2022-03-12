import logging

from celery import shared_task

from accounts.models import User
from accounts.verifiers.basic_verify import basic_verify
from .send_sms import send_sms_by_kavenegar
logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def basic_verify_user(user_id: int):
    user = User.objects.get(id=user_id)  # type: User

    basic_verify(user)
    alert_user_verify_status(user)


def alert_user_verify_status(user: User):
    from accounts.models import Notification
    if user.level >= User.LEVEL2 or user.verify_status == User.REJECTED:
        if user.level >= User.LEVEL2 and user.verify_status != User.REJECTED:
            title = 'احراز هویت سطح {} شما با موفقیت انجام شد'.format(user.level)
            message = 'احراز هویت سطح {} شما با موفقیت انجام شد'.format(user.level)
            level = Notification.SUCCESS
            template = 'levelup-accepted'

        else:
            title = 'اطلاعات وارد شده نیاز به بازنگری دارد.'
            message = 'اطلاعات احراز هویتی نیاز به بازنگری دارد'
            level = Notification.ERROR
            template = 'levelup-rejected'

        Notification.send(
            recipient=user,
            title=title,
            message=message,
            level=level
        )
        send_sms_by_kavenegar(
            phone=user.phone,
            template=template,
        )
