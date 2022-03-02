import logging

from celery import shared_task

from accounts.models import User, Notification
from accounts.verifiers.basic_verify import basic_verify

logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def basic_verify_user(user_id: int):
    user = User.objects.get(id=user_id)  # type: User

    try:
        basic_verify(user)
        alert_user_verify_status(user)

    except:
        user.refresh_from_db()
        if user.verify_status == User.PENDING:
            user.change_status(User.REJECTED)

        raise


def alert_user_verify_status(user: User):
    if user.verify_status in (User.VERIFIED, User.REJECTED):
        if user.verify_status == User.VERIFIED:
            title = 'شما احراز هویت شدید.'
            message = 'احراز هویت شما با موفقیت انجام شد.'
            level = Notification.SUCCESS
        else:
            title = 'اطلاعات وارد شده نیاز به بازنگری دارد.'
            message = 'اطلاعات احراز هویتی نیاز به بازنگری دارد'
            level = Notification.ERROR

        Notification.send(
            recipient=user,
            title=title,
            message=message,
            level=level
        )
