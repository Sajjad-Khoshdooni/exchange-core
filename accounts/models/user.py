from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

from accounts.utils import PHONE_MAX_LENGTH
from accounts.validators import mobile_number_validator


class User(AbstractUser):
    USERNAME_FIELD = 'phone'

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        validators=[mobile_number_validator],
        verbose_name='شماره تماس',
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'
        }
    )

    email_verified = models.BooleanField(default=False)
    email_verification_date = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get_user_from_login(cls, email_or_phone: str) -> 'User':
        return User.objects.filter(Q(phone=email_or_phone) | Q(email=email_or_phone)).first()
