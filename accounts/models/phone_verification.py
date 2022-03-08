import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from accounts.utils.validation import generate_random_code, PHONE_MAX_LENGTH, fifteen_minutes_later_datetime, MINUTES
from accounts.validators import mobile_number_validator, is_phone
from accounts.tasks import send_verification_code_by_kavenegar


class VerificationCode(models.Model):
    EXPIRATION_TIME = 15 * MINUTES

    SCOPE_FORGET_PASSWORD = 'forget'
    SCOPE_VERIFY_PHONE = 'verify'
    SCOPE_WITHDRAW = 'withdraw'
    SCOPE_TELEPHONE = 'tel'

    SCOPE_CHOICES = [
        (SCOPE_FORGET_PASSWORD, SCOPE_FORGET_PASSWORD), (SCOPE_VERIFY_PHONE, SCOPE_VERIFY_PHONE),
        (SCOPE_WITHDRAW, SCOPE_WITHDRAW), (SCOPE_TELEPHONE, SCOPE_TELEPHONE)
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
        default=generate_random_code,
        db_index=True,
        validators=[RegexValidator(r'^\d{6}$')]
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
        max_length=8,
        choices=SCOPE_CHOICES
    )

    @classmethod
    def get_by_code(cls, code: str, phone: str, scope: str) -> 'VerificationCode':
        return VerificationCode.objects.filter(
            code=code,
            code_used=False,
            expiration__gt=timezone.now(),
            scope=scope,
            phone=phone
        ).order_by('created').last()

    @classmethod
    def get_by_token(cls, token: str, scope: str) -> 'VerificationCode':
        return VerificationCode.objects.filter(
            token=token,
            token_used=False,
            created__gte=timezone.now() - timedelta(hours=1),
            scope=scope,
        ).first()

    @classmethod
    def send_otp_code(cls, phone: str, scope: str) -> 'VerificationCode':
        # todo: handle throttling (don't allow to send more than twice in minute per phone / scope)

        otp_code = VerificationCode.objects.create(
            phone=phone,
            scope=scope
        )

        if settings.DEBUG:
            print('[OTP] code for %s is: %s' % (otp_code.phone, otp_code.code))
        else:
            if scope != cls.SCOPE_TELEPHONE:  # is_phone(phone):
                send_type = 'sms'
                template = 'verify'
            else:
                send_type = 'call'
                template = 'telephone'

            send_verification_code_by_kavenegar(
                phone=otp_code.phone,
                code=otp_code.code,
                send_type=send_type,
                template=template
            )

        return otp_code

    def set_token_used(self):
        self.token_used = True
        self.save()
