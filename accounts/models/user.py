from uuid import uuid4

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from accounts.models import Notification
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
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

    SHIB, VOUCHER = 'true', 'voucher'

    USERNAME_FIELD = 'phone'

    FIAT, CRYPTO = 'fiat', 'crypto'

    NATIONAL_CODE_DUPLICATED = 'duplicated-national-code'

    objects = CustomUserManager()
    history = HistoricalRecords()

    chat_uuid = models.UUIDField(default=uuid4)

    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        validators=[mobile_number_validator],
        verbose_name='شماره موبایل',
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        error_messages={
            'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'
        }
    )

    first_name_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه نام',)
    last_name_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه نام خانوادگی',)

    national_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='کد ملی',
        db_index=True,
        validators=[national_card_code_validator],
    )
    national_code_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه کد ملی',)
    national_code_phone_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه کد ملی و موبایل (شاهکار)',)

    birth_date = models.DateField(null=True, blank=True, verbose_name='تاریخ تولد',)
    birth_date_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه تاریخ تولد',)

    level_2_verify_datetime = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تایید سطح ۲')
    level_3_verify_datetime = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تایید سطح 3')

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

    reject_reason = models.CharField(
        max_length=32,
        blank=True,
        choices=((NATIONAL_CODE_DUPLICATED, NATIONAL_CODE_DUPLICATED), )
    )

    first_fiat_deposit_date = models.DateTimeField(blank=True, null=True, verbose_name='زمان اولین واریز ریالی')

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
        db_index=True,
    )

    telephone_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه شماره تلفن')

    selfie_image_verified = models.BooleanField(null=True, blank=True, verbose_name='تاییدیه عکس سلفی')
    selfie_image_verifier = models.ForeignKey(
        to='accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='تایید کننده عکس سلفی'
    )

    archived = models.BooleanField(default=False, verbose_name='بایگانی')

    margin_quiz_pass_date = models.DateTimeField(null=True, blank=True)

    show_margin = models.BooleanField(default=True, verbose_name='امکان مشاهده حساب تعهدی')
    show_strategy_bot = models.BooleanField(default=False, verbose_name='امکان مشاهده ربات')
    show_community = models.BooleanField(default=False, verbose_name='امکان مشاهده کامیونیتی')
    show_staking = models.BooleanField(default=False, verbose_name='امکان مشاهده سرمایه‌گذاری')

    selfie_image_discard_text = models.TextField(blank=True, verbose_name='توضیحات رد کردن عکس سلفی')

    withdraw_before_48h_option = models.BooleanField(
        default=False,
        verbose_name='امکان برداشت وجه پیش از سپری شدن ۴۸ ساعت از اولین واریز',
    )

    can_withdraw = models.BooleanField(default=True)
    can_trade = models.BooleanField(default=True)

    withdraw_limit_whitelist = models.BooleanField(default=False)
    withdraw_risk_level_multiplier = models.PositiveIntegerField(
        default=1,
        choices=((1, 1), (2, 2), (3, 3), (5, 5), (10, 10), (20, 20), (40, 40))
    )

    promotion = models.CharField(max_length=256, blank=True, choices=((SHIB, SHIB), (VOUCHER, VOUCHER)))

    @property
    def kyc_bank_card(self):
        return self.bankcard_set.filter(kyc=True).first()

    def get_verify_weight(self) -> int:
        from accounts.models import FinotechRequest
        return FinotechRequest.objects.filter(
            user=self,
            search_key__isnull=False
        ).exclude(search_key='').aggregate(w=Sum('weight'))['w'] or 0

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

        constraints = [
            UniqueConstraint(
                fields=["national_code"],
                name="unique_verified_national_code",
                condition=Q(level__gt=1),
            )
        ]

    def change_status(self, status: str, reason: str = ''):
        from accounts.tasks.verify_user import alert_user_verify_status

        if self.verify_status != self.VERIFIED and status == self.VERIFIED:
            self.verify_status = self.INIT

            if self.level == User.LEVEL1:
                if User.objects.filter(level__gte=User.LEVEL2, national_code=self.national_code).exclude(id=self.id):
                    self.national_code_verified = False
                    self.save(update_fields=['national_code_verified'])
                    return self.change_status(User.REJECTED, User.NATIONAL_CODE_DUPLICATED)

            self.level += 1
            with transaction.atomic():
                if self.level == User.LEVEL2:
                    self.level_2_verify_datetime = timezone.now()

                elif self.level == User.LEVEL3:
                    self.level_3_verify_datetime = timezone.now()

                self.archived = False
                self.save(update_fields=['verify_status', 'level', 'level_2_verify_datetime', 'level_3_verify_datetime', 'archived'])

            if self.level == User.LEVEL2:
                from gamify.utils import check_prize_achievements, Task
                check_prize_achievements(self.account, Task.VERIFY_LEVEL2)

            alert_user_verify_status(self)

        elif self.verify_status != self.REJECTED and status == self.REJECTED:
            if self.level == self.LEVEL1:
                link = url_to_edit_object(self)
                send_support_message(
                    message='اطلاعات سطح %d کاربر مورد تایید قرار نگرفت. لطفا دستی بررسی شود.' % (self.level + 1),
                    link=link
                )

            self.verify_status = status
            self.reject_reason = reason
            self.save(update_fields=['verify_status', 'reject_reason'])

            alert_user_verify_status(self)

        else:
            self.verify_status = status
            self.archived = False
            self.save(update_fields=['verify_status', 'archived'])

    @property
    def primary_data_verified(self) -> bool:
        return self.first_name and self.first_name_verified and self.last_name and self.last_name_verified \
               and self.birth_date and self.birth_date_verified

    def get_level2_verify_fields(self):
        from financial.models import BankCard

        bank_card_verified = None

        if BankCard.live_objects.filter(user=self, verified=True):
            bank_card_verified = True
        elif not BankCard.live_objects.filter(user=self, verified__isnull=True):
            bank_card_verified = False

        return [
            bool(self.national_code),
            bool(self.birth_date), self.birth_date_verified,
            bool(self.first_name), self.first_name_verified,
            bool(self.last_name), self.last_name_verified,
            bank_card_verified
        ]

    def verify_level2_if_not(self) -> bool:
        if self.level == User.LEVEL1 and all(self.get_level2_verify_fields()):
            self.change_status(User.VERIFIED)

            return True

        return False

    def reject_level2_if_should(self) -> bool:

        if self.level == User.LEVEL1 and self.verify_status == self.PENDING:
            level2_fields = self.get_level2_verify_fields()
            any_none = list(filter(lambda f: f is None, level2_fields))

            if not all(level2_fields) and not any_none:
                self.change_status(User.REJECTED)
                return True

        return False

    @classmethod
    def get_user_from_login(cls, email_or_phone: str) -> 'User':
        return User.objects.filter(Q(phone=email_or_phone) | Q(email=email_or_phone)).first()

    def save(self, *args, **kwargs):
        old = self.id and User.objects.get(id=self.id)
        creating = not self.id
        super(User, self).save(*args, **kwargs)

        if creating:
            from accounts.models import Account
            Account.objects.create(user=self)

        if self.level == self.LEVEL2 and self.verify_status == self.PENDING:
            if self.national_code_phone_verified and self.selfie_image_verified:
                self.change_status(self.VERIFIED)
            else:
                fields = [self.selfie_image_verified]
                any_false = any(map(lambda f: f is False, fields))

                if any_false:
                    self.change_status(self.REJECTED)

        elif self.level == self.LEVEL1 and self.verify_status == self.PENDING:
            self.reject_level2_if_should()
            self.verify_level2_if_not()

        if old and old.selfie_image_verified is None and self.selfie_image_verified is False:
            Notification.send(
                recipient=self,
                title='عکس سلفی شما تایید نشد',
                level=Notification.ERROR,
                message=self.selfie_image_discard_text
            )
            self.selfie_image_discard_text = ''
            super(User, self).save(*args, **kwargs)
