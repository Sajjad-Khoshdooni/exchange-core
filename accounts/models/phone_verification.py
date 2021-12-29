import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from accounts.utils import generate_random_code, PHONE_MAX_LENGTH, fifteen_minutes_later_datetime, MINUTES
from accounts.validators import mobile_number_validator
from accounts.tasks import send_verification_code_by_kavenegar


class VerificationCode(models.Model):
    EXPIRATION_TIME = 15 * MINUTES

    SCOPE_FORGET_PASSWORD = 'forget'
    SCOPE_VERIFY_PHONE = 'verify'

    SCOPE_CHOICES = [(SCOPE_FORGET_PASSWORD, SCOPE_FORGET_PASSWORD), (SCOPE_VERIFY_PHONE, SCOPE_VERIFY_PHONE)]

    created = models.DateTimeField(auto_now_add=True)
    expiration = models.DateTimeField(default=fifteen_minutes_later_datetime)

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        validators=[mobile_number_validator],
        verbose_name='شماره تماس',
        db_index=True
    )

    code = models.CharField(
        max_length=6,
        default=generate_random_code,
        db_index=True,
        validators=[RegexValidator(r'^\d{6}$')]
    )

    used = models.BooleanField(
        default=False,
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )

    scope = models.CharField(
        max_length=8,
        choices=SCOPE_CHOICES
    )

    @classmethod
    def get_otp_code(cls, code: str, phone: str, scope: str) -> 'VerificationCode':
        return VerificationCode.objects.filter(
            code=code,
            used=False,
            expiration__gt=timezone.now(),
            scope=scope,
            phone=phone
        ).order_by('created').last()

    @classmethod
    def send_otp_code(cls, phone: str, scope: str) -> 'VerificationCode':
        # todo: handle throttling

        otp_code = VerificationCode.objects.create(
            phone=phone,
            scope=scope
        )

        if settings.DEBUG:
            print('[OTP] code for %s is: %s' % (otp_code.phone, otp_code.code))
        else:
            send_verification_code_by_kavenegar(
                phone=otp_code.phone,
                code=otp_code.code,
                created=otp_code.created,
            )

        return otp_code
