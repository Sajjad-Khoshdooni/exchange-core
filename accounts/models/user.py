from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q

from accounts.utils.validation import PHONE_MAX_LENGTH
from accounts.validators import mobile_number_validator, national_card_code_validator


class CustomUserManager(UserManager):
    def create_superuser(self, email=None, password=None, **extra_fields):
        return super(CustomUserManager, self).create_superuser(extra_fields['phone'], email, password, **extra_fields)


class User(AbstractUser):
    LEVEL1 = 1
    LEVEL2 = 2
    LEVEL3 = 3

    INIT, PENDING, REJECTED, VERIFIED = 'init', 'pending', 'rejected', 'verified'

    USERNAME_FIELD = 'phone'

    objects = CustomUserManager()

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

    first_name_verified = models.BooleanField(null=True, blank=True)
    last_name_verified = models.BooleanField(null=True, blank=True)

    national_code = models.CharField(
        max_length=10,
        blank=True,
        validators=[national_card_code_validator],
    )
    national_code_verified = models.BooleanField(null=True, blank=True)

    birth_date = models.DateField(null=True, blank=True)
    birth_date_verified = models.BooleanField(null=True, blank=True)

    level = models.PositiveSmallIntegerField(
        default=LEVEL1,
        choices=(
            (LEVEL1, 'level 1'), (LEVEL2, 'level 2'), (LEVEL3, 'level 3')
        )
    )

    verify_status = models.CharField(
        max_length=8,
        choices=((INIT, INIT), (PENDING, PENDING), (REJECTED, REJECTED), (VERIFIED, VERIFIED)),
        default=INIT,
    )

    first_fiat_deposit_date = models.DateTimeField(blank=True, null=True)

    def change_status(self, status: str):
        if self.verify_status == self.PENDING and status == self.VERIFIED:
            self.verify_status = self.INIT
            self.level += 1
        else:
            self.verify_status = status

        self.save()

    @property
    def primary_data_verified(self):
        return self.first_name and self.first_name_verified and self.last_name and self.last_name_verified and \
            self.birth_date and self.birth_date_verified

    @classmethod
    def get_user_from_login(cls, email_or_phone: str) -> 'User':
        return User.objects.filter(Q(phone=email_or_phone) | Q(email=email_or_phone)).first()

    def save(self, *args, **kwargs):
        creating = not self.id
        super(User, self).save(*args, **kwargs)

        if creating:
            from accounts.models import Account
            Account.objects.create(user=self)
