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

    SCOPE_TRIGGER_UPGRADE_LEVEL_FIRST = 'scope_trigger_upgrade_level-first'
    SCOPE_TRIGGER_UPGRADE_LEVEL_SECOND = 'scope-trigger_upgrade_level_second'
    SCOPE_TRIGGER_UPGRADE_LEVEL_THIRD = 'scope_trigger_upgrade_level_third'

    SCOPE_TRIGGER_DEPOSIT_FIRST = 'scope_trigger_deposit_first'
    SCOPE_TRIGGER_DEPOSIT_SECOND = 'scope_trigger_deposit_second'
    SCOPE_TRIGGER_DEPOSIT_THIRD = 'scope_trigger_deposit_third'
    SCOPE_TRIGGER_DEPOSIT_FOURTH = 'scope_trigger_deposit_fourth'

    SCOPE_TRIGGER_TRADE_FIRST = 'scope_trigger_trade_first'
    SCOPE_TRIGGER_TRADE_SECOND = 'scope_trigger_trade_second'
    SCOPE_TRIGGER_TRADE_THIRD = 'scope_trigger_trade_third'

    SCOPE_CHOICES = (
        (SCOPE_LEVEL_2_PRIZE, SCOPE_LEVEL_2_PRIZE),
        (SCOPE_FIRST_FIAT_DEPOSIT_PRIZE, SCOPE_FIRST_FIAT_DEPOSIT_PRIZE),
        (SCOPE_TRADE_PRIZE, SCOPE_TRADE_PRIZE),
        (SCOPE_MARGIN_ENABLE, SCOPE_MARGIN_ENABLE),
        (SCOPE_TRIGGER_UPGRADE_LEVEL_FIRST, SCOPE_TRIGGER_UPGRADE_LEVEL_FIRST),
        (SCOPE_TRIGGER_UPGRADE_LEVEL_SECOND, SCOPE_TRIGGER_UPGRADE_LEVEL_SECOND),
        (SCOPE_TRIGGER_UPGRADE_LEVEL_THIRD, SCOPE_TRIGGER_UPGRADE_LEVEL_THIRD),
        (SCOPE_TRIGGER_DEPOSIT_FIRST, SCOPE_TRIGGER_DEPOSIT_FIRST),
        (SCOPE_TRIGGER_DEPOSIT_SECOND, SCOPE_TRIGGER_DEPOSIT_SECOND),
        (SCOPE_TRIGGER_DEPOSIT_THIRD, SCOPE_TRIGGER_DEPOSIT_THIRD),
        (SCOPE_TRIGGER_DEPOSIT_FOURTH, SCOPE_TRIGGER_DEPOSIT_FOURTH),
        (SCOPE_TRIGGER_TRADE_FIRST, SCOPE_TRIGGER_TRADE_FIRST),
        (SCOPE_TRIGGER_TRADE_SECOND, SCOPE_TRIGGER_TRADE_SECOND),
        (SCOPE_TRIGGER_TRADE_THIRD, SCOPE_TRIGGER_TRADE_THIRD),
    )

    created = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        verbose_name='شماره تماس',
        db_index=True
    )
    scope = models.CharField(
        max_length=40,
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
                'brand': '{} و دریافت هدیه تا ۲۰۰ هزار شیبا،'.format(config('BRAND')),
                'department': config('RETENTION_URL_VERIFY')
            }

        elif scope == cls.SCOPE_FIRST_FIAT_DEPOSIT_PRIZE:
            template = '67758'
            params = {
                'name': 'صرافی {}'.format(config('BRAND')),
                'brand': 'و دریافت هدیه تا ۲۰۰ هزار شیبا به {}'.format(config('BRAND')),
                'department': config('RETENTION_URL_DEPOSIT')
            }

        elif scope == cls.SCOPE_TRADE_PRIZE:
            template = '67764'
            params = {
                'name': 'تا ۲۰۰ هزار شیبا هدیه {}'.format(config('BRAND')),
                'brand': 'صرافی {}'.format(config('BRAND')),
                'department': config('RETENTION_URL_TRADE'),
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
