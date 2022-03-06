from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q
from simple_history.models import HistoricalRecords
from django.utils import timezone
from accounts.utils.validation import PHONE_MAX_LENGTH
from accounts.validators import mobile_number_validator, national_card_code_validator, telephone_number_validator


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
    history = HistoricalRecords()

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        validators=[mobile_number_validator],
        verbose_name='شماره موبایل',
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'
        }
    )

    email_verified = models.BooleanField(default=False,verbose_name='تاییدیه ایمیل',)
    email_verification_date = models.DateTimeField(null=True, blank=True)

    first_name_verified = models.BooleanField(null=True, blank=True,verbose_name='تاییدیه نام',)
    last_name_verified = models.BooleanField(null=True, blank=True,verbose_name='تاییدیه نام خانوادگی',)

    national_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='کد ملی',
        validators=[national_card_code_validator],
    )
    national_code_verified = models.BooleanField(null=True, blank=True,verbose_name='تاییدیه کد ملی',)

    birth_date = models.DateField(null=True, blank=True,verbose_name='تاریخ تولد',)
    birth_date_verified = models.BooleanField(null=True, blank=True,verbose_name='تاییدیه تاریخ تولد',)

    level_2_verify_datetime = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تاپید سطح ۲')
    level_3_verify_datetime = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تاپید سطح 3')

    level = models.PositiveSmallIntegerField(
        default=LEVEL1,
        choices=(
            (LEVEL1, 'level 1'), (LEVEL2, 'level 2'), (LEVEL3, 'level 3')

        ),
        verbose_name='سطح',
    )

    verify_status = models.CharField(
        max_length=8,
        choices=((INIT, INIT), (PENDING, PENDING), (REJECTED, REJECTED), (VERIFIED, VERIFIED)),
        default=INIT,
        verbose_name='وضعیت تایید'
    )

    first_fiat_deposit_date = models.DateTimeField(blank=True, null=True, verbose_name='زمان اولین برداشت ریالی')

    national_card_image = models.OneToOneField(
        to='multimedia.Image',
        on_delete=models.PROTECT,
        verbose_name='عکس کارت ملی',
        related_name='+',
        blank=True,
        null=True
    )
    selfie_image = models.OneToOneField(
        to='multimedia.Image',
        on_delete=models.PROTECT,
        verbose_name='عکس سلفی',
        related_name='+',
        blank=True,
        null=True
    )
    telephone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        validators=[telephone_number_validator],
        verbose_name='شماره تلفن',
        blank=True,
        null=True,
        unique=True,
        error_messages={
            'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'
        }
    )

    national_card_image_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه عکس کارت ملی')
    selfie_image_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه عکس سلفی')
    telephone_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه شماره تلفن')

    def change_status(self, status: str):
        if self.verify_status == self.PENDING and status == self.VERIFIED:
            self.verify_status = self.INIT
            self.level += 1
            if self.level == User.LEVEL2:
                self.level_2_verify_datetime = timezone.now()
            if self.level == User.LEVEL3:
                self.level_3_verify_datetime = timezone.now()
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

        if self.level == self.LEVEL2 and self.telephone_verified and self.national_card_image_verified \
                and self.selfie_image_verified:

            self.verify_status = self.PENDING
            self.change_status(self.VERIFIED)
