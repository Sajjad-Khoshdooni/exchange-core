
import logging

from celery import shared_task
from decouple import config

from accounts.models import Notification
from accounts.models import User
from accounts.verifiers.jibit_basic_verify import basic_verify, verify_national_code_with_phone
from .send_sms import send_message_by_kavenegar

logger = logging.getLogger(__name__)


@shared_task(queue='kyc')
def basic_verify_user(user_id: int):
    user = User.objects.get(id=user_id)  # type: User
    basic_verify(user)


@shared_task(queue='kyc')
def verify_user_national_code(user_id: int):
    user = User.objects.get(id=user_id)  # type: User
    verify_national_code_with_phone(user)


def alert_user_verify_status(user: User):
    if user.verify_status == User.PENDING:
        return

    notif_message = ''

    if user.level >= User.LEVEL2 or user.verify_status == User.REJECTED:
        if user.verify_status == User.REJECTED:
            if user.reject_reason == User.NATIONAL_CODE_DUPLICATED:
                title = 'کد ملی تکراری است. لطفا به حساب اصلی‌تان وارد شوید.'
                notif_message = 'شما قبلا در {} با شماره موبایل دیگری ثبت‌نام کرده‌اید و احراز هویت‌تان انجام شده است. لطفا از آن حساب استفاده کنید.'.format(
                    config('BRAND'))
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
