import logging
import uuid
from datetime import timedelta
from typing import Union

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from yekta_config.config import config

from accounts.utils.validation import generate_random_code, PHONE_MAX_LENGTH, fifteen_minutes_later_datetime, MINUTES

logger = logging.getLogger(__name__)


class VerificationCode(models.Model):
    EXPIRATION_TIME = 15 * MINUTES

    SCOPE_FORGET_PASSWORD = 'forget'
    SCOPE_VERIFY_PHONE = 'verify'
    SCOPE_VERIFY_EMAIL = 'email_verify'
    SCOPE_CRYPTO_WITHDRAW = 'withdraw'
    SCOPE_FIAT_WITHDRAW = 'fiat_withdraw'
    SCOPE_TELEPHONE = 'tel'
    SCOPE_CHANGE_PASSWORD = 'change_pass'
    SCOPE_CHANGE_PHONE = 'change_phone'
    SCOPE_2FA_ACTIVATE = '2fa_activate'

    SCOPE_CHOICES = [
        (SCOPE_FORGET_PASSWORD, SCOPE_FORGET_PASSWORD), (SCOPE_VERIFY_PHONE, SCOPE_VERIFY_PHONE),
        (SCOPE_CRYPTO_WITHDRAW, SCOPE_CRYPTO_WITHDRAW), (SCOPE_TELEPHONE, SCOPE_TELEPHONE),
        (SCOPE_CHANGE_PASSWORD, SCOPE_CHANGE_PASSWORD), (SCOPE_CHANGE_PHONE, SCOPE_CHANGE_PHONE),
        (SCOPE_VERIFY_EMAIL, SCOPE_VERIFY_EMAIL), (SCOPE_FIAT_WITHDRAW, SCOPE_FIAT_WITHDRAW),
        (SCOPE_2FA_ACTIVATE, SCOPE_2FA_ACTIVATE),
    ]

    created = models.DateTimeField(auto_now_add=True)
    expiration = models.DateTimeField(default=fifteen_minutes_later_datetime)

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        verbose_name='شماره تماس',
        db_index=True
    )

    code = models.CharField(
        max_length=6,
        db_index=True,
        validators=[RegexValidator(r'^\d{4,6}$')]
    )

    code_used = models.BooleanField(
        default=False,
    )

    token_used = models.BooleanField(
        default=False,
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )

    scope = models.CharField(
        max_length=32,
        choices=SCOPE_CHOICES
    )

    user = models.ForeignKey(
        to='accounts.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    @classmethod
    def get_by_code(cls, code: str, phone: str, scope: str, user=None) -> 'VerificationCode':
        otp_codes = VerificationCode.objects.filter(
            code=code,
            code_used=False,
            expiration__gt=timezone.now(),
            scope=scope,
            phone=phone
        )

        if user:
            otp_codes = otp_codes.filter(user=user)

        return otp_codes.order_by('created').last()

    @classmethod
    def get_by_token(cls, token: str, scope: str) -> 'VerificationCode':
        return VerificationCode.objects.filter(
            token=token,
            token_used=False,
            created__gte=timezone.now() - timedelta(hours=1),
            scope=scope,
        ).first()

    @classmethod
    def send_otp_code(cls, phone: str, scope: str, user=None) -> Union['VerificationCode', None]:
        # todo: handle throttling (don't allow to send more than twice in minute per phone / scope)
        # todo: use user devices / ip , ...

        if phone == '09120889956':
            logger.info('[OTP] Ignored sending otp to kavenegar due to blacklist')
            return

        if not settings.DEBUG_OR_TESTING:

            any_recent_code = VerificationCode.objects.filter(
                phone=phone,
                created__gte=timezone.now() - timedelta(minutes=2),
            ).exists()

            if not settings.DEBUG_OR_TESTING_OR_STAGING and any_recent_code:
                logger.info('[OTP] Ignored sending otp to kavenegar because of recent')
                return

            prev_codes = VerificationCode.objects.filter(
                phone=phone,
                created__gte=timezone.now() - timedelta(minutes=15),
            ).count()

            if not settings.DEBUG_OR_TESTING_OR_STAGING and prev_codes >= 3:
                logger.info('[OTP] Ignored sending otp to kavenegar because of multiple prev')
                return

        if scope in (cls.SCOPE_TELEPHONE, cls.SCOPE_VERIFY_PHONE):
            code_length = 4
        else:
            code_length = 6

        if settings.DEBUG_OR_TESTING_OR_STAGING:
            code = '1' * code_length
        else:
            code = generate_random_code(code_length)

        otp_code = VerificationCode.objects.create(
            phone=phone,
            scope=scope,
            code=code,
            user=user,
        )

        if settings.DEBUG_OR_TESTING_OR_STAGING:
            print('[OTP] code for %s is: %s' % (otp_code.phone, otp_code.code))
        else:
            if scope != cls.SCOPE_TELEPHONE:  # is_phone(phone):
                send_type = 'sms'
                template = 'verify'
            else:
                send_type = 'call'
                template = 'telephone'

            if config('OTP_BY_SMS_IR', cast=bool, default=False):
                from accounts.tasks import send_message_by_sms_ir
                send_message_by_sms_ir(
                    phone=phone,
                    template='69129',
                    params={
                        'brand': config('BRAND'),
                        'code': otp_code.code
                    }
                )
            else:
                from accounts.tasks import send_message_by_kavenegar
                send_message_by_kavenegar(
                    phone=otp_code.phone,
                    token=otp_code.code,
                    send_type=send_type,
                    template=template
                )

        return otp_code

    def set_code_used(self):
        self.code_used = True
        self.save()

    def set_token_used(self):
        self.token_used = True
        self.save()
