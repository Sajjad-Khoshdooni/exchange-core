from django.conf import settings
from django.db import models
from yekta_config.config import config

from accounts.models import User
from accounts.utils.validation import PHONE_MAX_LENGTH


class ExternalNotification(models.Model):

    SCOPE_LEVEL_2_PRIZE = 'level_2_prize'
    SCOPE_FIRST_FIAT_DEPOSIT_PRIZE = 'first_deposit_prize'
    SCOPE_TRADE_PRIZE = 'trade_prize'
    SCOPE_MARGIN_ENABLE = 'margin_enable'

    SCOPE_CHOICES = (
        (SCOPE_LEVEL_2_PRIZE, SCOPE_LEVEL_2_PRIZE),
        (SCOPE_FIRST_FIAT_DEPOSIT_PRIZE, SCOPE_FIRST_FIAT_DEPOSIT_PRIZE),
        (SCOPE_TRADE_PRIZE, SCOPE_TRADE_PRIZE)
    )

    created = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        verbose_name='شماره تماس',
        db_index=True
    )
    scope = models.CharField(
        max_length=22,
        choices=SCOPE_CHOICES,
        verbose_name='نوع'
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    @classmethod
    def send_sms(cls, user: User, scope: str, ):
        from accounts.tasks import send_message_by_sms_ir
        if scope == cls.SCOPE_LEVEL_2_PRIZE:
            template = '67757'

            params = {
                'brand': '{} و دریافت سی هزار شیبا،'.format(config('BRAND')),
                'department': config('RETENTION_URL_VERIFY')
            }

        elif scope == cls.SCOPE_FIRST_FIAT_DEPOSIT_PRIZE:
            template = '67758'
            params = {
                'name': 'صرافی {}'.format(config('BRAND')),
                'brand': 'و دریافت هدیه سی هزار شیبا به {}'.format(config('BRAND')),
                'department': config('RETENTION_URL_DEPOSIT')
            }

        elif scope == cls.SCOPE_TRADE_PRIZE:
            template = '67764'
            params = {
                'name': 'سی هزار شیبا هدیه {}'.format(config('BRAND')),
                'department': config('RETENTION_URL_TRADE')
            }

        elif scope == cls.SCOPE_MARGIN_ENABLE:
            template = '67896'
            params = {
                'brand': 'راستین'
            }

        else:
            raise NotImplementedError

        if settings.DEBUG_OR_TESTING:
            print('template={},phone={},params={}'.format(template, user.phone, params))
            return

        resp = send_message_by_sms_ir(
            phone=user.phone,
            params=params,
            template=template
        )

        if resp:
            ExternalNotification.objects.create(phone=user.phone, scope=scope, user=user)

    @staticmethod
    def get_users_sent_sms_notif(scope: str):
        return ExternalNotification.objects.filter(scope=scope).values_list('user_id')

    class Meta:
        verbose_name = verbose_name_plural = 'نوتیف‌های بیرون پنل'
