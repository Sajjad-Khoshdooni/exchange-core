from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

from accounts.validators import mobile_number_validator


class User(AbstractUser):
    USERNAME_FIELD = 'phone'

    phone = models.CharField(
        max_length=16,
        validators=[mobile_number_validator],
        verbose_name='شماره تماس',
        unique=True,
        error_messages={
            'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'
        }
    )

    @classmethod
    def get_user_from_login(cls, email_or_phone: str) -> 'User':
        return User.objects.filter(Q(phone=email_or_phone) | Q(email=email_or_phone)).first()


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
