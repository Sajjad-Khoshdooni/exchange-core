from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from accounts.models import User
from django.utils import timezone
from accounts.utils.validation import generate_random_code, fifteen_minutes_later_datetime, MINUTES
from django.template.loader import get_template
from django.core.mail import EmailMessage


class EmailVerificationCode(models.Model):
    EXPIRATION_TIME = 15 * MINUTES

    SCOPE_FORGET_PASSWORD = 'forget'
    SCOPE_VERIFY_EMAIL = 'verify'

    SCOPE_CHOICES = [
        (SCOPE_FORGET_PASSWORD, SCOPE_FORGET_PASSWORD), (SCOPE_VERIFY_EMAIL, SCOPE_VERIFY_EMAIL),
    ]

    created = models.DateTimeField(auto_now_add=True)
    expiration = models.DateTimeField(default=fifteen_minutes_later_datetime)

    email = models.EmailField(
        verbose_name='ایمیل',
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

    scope = models.CharField(
        max_length=8,
        choices=SCOPE_CHOICES
    )

    user = models.ForeignKey(
        to='accounts.User',
        on_delete=models.CASCADE,
    )

    @classmethod
    def get_by_code(cls, code: str, user: User, scope: str,) -> 'EmailVerificationCode':
        otp_codes = EmailVerificationCode.objects.filter(
            code=code,
            code_used=False,
            expiration__gt=timezone.now(),
            scope=scope,
            user=user
        )

        return otp_codes.order_by('created').last()

    @classmethod
    def send_otp_code(cls, email: str, scope: str, user) -> 'EmailVerificationCode':
        # todo: handle throttling (don't allow to send more than twice in minute per email / scope)

        code_length = 6

        otp_code = EmailVerificationCode.objects.create(
            email=email,
            scope=scope,
            code=generate_random_code(code_length),
            user=user,
        )

        if settings.DEBUG:
            print('[OTP] code for %s is: %s' % (otp_code.email, otp_code.code))
        else:

            message = get_template("accounts/email_content.html").render(
                {'context': otp_code.code}
            )
            mail = EmailMessage(
                subject='Subject here',
                body=message,
                to=[email],
            )
            mail.content_subtype = "html"
            mail.send()

        return otp_code

    def set_code_used(self):
        self.code_used = True
        self.save()

