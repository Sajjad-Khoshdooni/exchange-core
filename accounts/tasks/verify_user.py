
import logging
from celery import shared_task
from accounts.models import Notification
from accounts.models import User
from accounts.verifiers.basic_verify import basic_verify
from .send_sms import send_message_by_kavenegar

logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def basic_verify_user(user_id: int):
    user = User.objects.get(id=user_id)  # type: User

    basic_verify(user)
    alert_user_verify_status(user)


def alert_user_verify_status(user: User):
    if user.verify_status == User.PENDING:
        return

    notif_message = ''

    if user.level >= User.LEVEL2 or user.verify_status == User.REJECTED:
        if user.verify_status == User.REJECTED:
            if user.national_code_duplicated_alert:
                title = 'کد ملی تکراری است. لطفا به حساب اصلی‌تان وارد شوید.'
                notif_message = 'شما قبلا در راستین با شماره موبایل دیگری ثبت‌نام کرده‌اید و احراز هویت‌تان انجام شده است. لطفا از آن حساب استفاده کنید.'
            else:
                title = 'اطلاعات وارد شده نیاز به بازنگری دارد.'

            level = Notification.ERROR
            template = 'levelup-rejected'
            levelup = user.level + 1
        else:
            title = 'احراز هویت سطح {} شما با موفقیت انجام شد.'.format(user.level)
            level = Notification.SUCCESS
            template = 'levelup-accepted'
            levelup = user.level

        Notification.send(
            recipient=user,
            title=title,
            level=level,
            message=notif_message
        )
        send_message_by_kavenegar(
            phone=user.phone,
            template=template,
            token=str(levelup)
        )


def alert_user_prize(user: User, scope: str):
    from ledger.models import Prize
    level = Notification.SUCCESS

    if scope == Prize.SIGN_UP_PRIZE:
        title = '۱۰۰۰شیبا به کیف پول شما اضافه شد.'

    if scope == Prize.LEVEL2_PRIZE:
        title = '۱۰۰۰شیبا به کیف پول شما اضافه شد.'

    if scope == Prize.FIRST_TRADE_PRIZE:
        title = '۱۰۰۰شیبا به کیف پول شما اضافه شد.'

    Notification.send(
        recipient=user,
        title=title,
        level=level
    )







