from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import Q

from account.utils import PHONE_MAX_LENGTH
from account.validators import mobile_number_validator


class CustomUserManager(UserManager):
    def create_superuser(self, email=None, password=None, **extra_fields):
        return super(CustomUserManager, self).create_superuser(extra_fields['phone'], email, password, **extra_fields)


class User(AbstractUser):
    objects = CustomUserManager()

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

    def save(self, *args, **kwargs):
        creating = not self.id
        super(User, self).save(*args, **kwargs)

        if creating:
            from account.models import Account
            Account.objects.create(user=self)
