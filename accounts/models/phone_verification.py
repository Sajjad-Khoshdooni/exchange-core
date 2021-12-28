import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.utils import generate_random_code, PHONE_MAX_LENGTH, fifteen_minutes_later_datetime, MINUTES
from accounts.validators import mobile_number_validator
from accounts.tasks import send_verification_code_by_kavenegar


class VerificationCode(models.Model):
    EXPIRATION_TIME = 15 * MINUTES
    TIME_TO_REQUEST_ANOTHER_CODE = 3 * MINUTES

    created = models.DateTimeField(auto_now_add=True)
    expiration = models.DateTimeField(default=fifteen_minutes_later_datetime)

    phone_number = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        validators=[mobile_number_validator],
        verbose_name='شماره تماس',
        db_index=True
    )

    code = models.CharField(
        max_length=6,
        default=generate_random_code,
        db_index=True,
    )

    used = models.BooleanField(
        default=False,
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )

    @classmethod
    def get_otp_code(cls, code: str) -> 'VerificationCode':
        return VerificationCode.objects.filter(
            code=code,
            used=False,
            expiration__gt=timezone.now(),
        ).order_by('created').last()

    @classmethod
    def send_otp_code(cls, phone_number: str) -> 'VerificationCode':
        # todo: handle throttling

        otp_code = cls.objects.create(phone_number=phone_number)

        if settings.DEBUG:
            print('[OTP] code for %s is: %s' % (otp_code.phone_number, otp_code.code))
        else:
            send_verification_code_by_kavenegar(
                phone_number=otp_code.phone_number,
                code=otp_code.code,
                created=otp_code.created,
            )

        return otp_code
