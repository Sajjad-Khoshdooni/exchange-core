from django.conf import settings
from django.db import models
from decouple import config

from accounts.models import User
from accounts.utils.validation import PHONE_MAX_LENGTH


class ExternalNotification(models.Model):

    SCOPE_FIRST_FIAT_DEPOSIT_PRIZE = 'first_deposit_prize'
    SCOPE_TRADE_PRIZE = 'trade_prize'
    SCOPE_MARGIN_ENABLE = 'margin_enable'

    SCOPE_TOP_GAINERS = 'top_gainers'

    SCOPE_VERIFY1 = 'scope_verify1'
    SCOPE_VERIFY2 = 'scope-verify2'
    SCOPE_VERIFY3 = 'scope_verify3'

    SCOPE_DEPOSIT1 = 'scope_deposit1'
    SCOPE_DEPOSIT2 = 'scope_deposit2'
    SCOPE_DEPOSIT3 = 'scope_deposit3'
    SCOPE_DEPOSIT4 = 'scope_deposit4'

    SCOPE_TRADE1 = 'scope_trade1'
    SCOPE_TRADE2 = 'scope_trade2'
    SCOPE_TRADE3 = 'scope_trade3'

    TEMPLATES = {
        SCOPE_MARGIN_ENABLE: {
            'template': '67896',
            'params': {
                'brand': settings.BRAND,
            }
        },
        SCOPE_TOP_GAINERS: {
            'template': '68120',
            'params': {
                'name': '{count} کوین {percent} درصد',
                'brand': 'و دریافت تا ۲۰۰ هزار شیبا به صرافی {}'.format(settings.BRAND),
                'department': config('RETENTION_URL_TOP_GAINERS', ''),
            }
        },

        SCOPE_VERIFY1: {
            'template': '67757',
            'params': {
                'brand': 'صرافی {} و دریافت تا ۲۰۰ هزار شیبا،'.format(settings.BRAND),
                'department': config('RETENTION_URL_VERIFY', '')
            }
        },

        SCOPE_VERIFY2: {
            'template': '67757',
            'params': {
                'brand': 'صرافی {} و دریافت تا ۲۰۰ هزار شیبا،'.format(settings.BRAND),
                'department': config('RETENTION_URL_VERIFY', '')
            }
        },

        SCOPE_VERIFY3: {
            'template': '68113',
            'params': {
                'name': 'آخرین فرصت دریافت تا ۲۰۰ هزار شیبا در {}.'.format(settings.BRAND),
                'department': config('RETENTION_URL_VERIFY', '')
            }
        },

        SCOPE_DEPOSIT1: {
            'template': '67758',
            'params': {
                'name': 'صرافی {}'.format(settings.BRAND),
                'brand': 'و دریافت هدیه تا ۲۰۰ هزار شیبا به {}'.format(settings.BRAND),
                'department': config('RETENTION_URL_DEPOSIT', '')
            }
        },
        SCOPE_DEPOSIT2: {
            'template': '68105',
            'params': {
                'name': '{} تنها صرافی با کارمزد صفر.'.format(settings.BRAND),
                'brand': 'و دریافت هدیه تا ۲۰۰ هزار شیبا به {}'.format(settings.BRAND),
                'department': config('RETENTION_URL_DEPOSIT', '')
            }
        },
        SCOPE_DEPOSIT3: {
            'template': '68106',
            'params': {
                'name': 'تا آخر هفته فرصت دارید با',
                'brand': 'در صرافی {} تا ۲۰۰ هزار شیبا هدیه بگیرید.'.format(settings.BRAND),
                'department': config('RETENTION_URL_DEPOSIT', '')
            }
        },
        SCOPE_DEPOSIT4: {
            'template': '68106',
            'params': {
                'name': 'تا امشب فرصت دارید با',
                'brand': 'در صرافی {} تا ۲۰۰ هزار شیبا هدیه بگیرید.'.format(settings.BRAND),
                'department': config('RETENTION_URL_DEPOSIT', '')
            }
        },

        SCOPE_TRADE1: {
            'template': '68107',
            'params': {
                'name': 'صرافی {} با کارمزد صفر'.format(settings.BRAND),
                'brand': 'و تا ۲۰۰ هزار شیبا هدیه بگیرید',
                'department': config('RETENTION_URL_TRADE', '')
            }
        },

        SCOPE_TRADE2: {
            'template': '68107',
            'params': {
                'name': 'صرافی {} تا امشب'.format(settings.BRAND),
                'brand': 'و تا ۲۰۰ هزار شیبا هدیه بگیرید',
                'department': config('RETENTION_URL_TRADE', '')
            }
        },
        SCOPE_TRADE3: {
            'template': '68107',
            'params': {
                'name': 'صرافی {} تا امشب'.format(settings.BRAND),
                'brand': 'و تا ۲۰۰ هزار شیبا هدیه بگیرید',
                'department': config('RETENTION_URL_TRADE', '')
            }
        },
    }

    SCOPE_CHOICES = (
        (SCOPE_TOP_GAINERS, SCOPE_TOP_GAINERS),
        (SCOPE_MARGIN_ENABLE, SCOPE_MARGIN_ENABLE),
        (SCOPE_VERIFY1, SCOPE_VERIFY1),
        (SCOPE_VERIFY2, SCOPE_VERIFY2),
        (SCOPE_VERIFY3, SCOPE_VERIFY3),
        (SCOPE_DEPOSIT1, SCOPE_DEPOSIT1),
        (SCOPE_DEPOSIT2, SCOPE_DEPOSIT2),
        (SCOPE_DEPOSIT3, SCOPE_DEPOSIT3),
        (SCOPE_DEPOSIT4, SCOPE_DEPOSIT4),
        (SCOPE_TRADE1, SCOPE_TRADE1),
        (SCOPE_TRADE2, SCOPE_TRADE2),
        (SCOPE_TRADE3, SCOPE_TRADE3),
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
    def send_sms(cls, user: User, scope: str, params_converter=None) -> bool:
        from accounts.tasks import send_message_by_sms_ir

        if settings.DEBUG_OR_TESTING:
            print('scope={},phone={}'.format(scope, user.phone))
            return True

        data = cls.TEMPLATES[scope]
        params = data['params']

        if params_converter:
            params = params_converter(params)

        resp = send_message_by_sms_ir(
            phone=user.phone,
            params=params,
            template=data['template']
        )

        if resp:
            ExternalNotification.objects.create(phone=user.phone, scope=scope, user=user)

        return bool(resp)

    @staticmethod
    def get_users_sent_sms_notif(scope: str):
        return ExternalNotification.objects.filter(scope=scope).values_list('user_id')

    class Meta:
        verbose_name = verbose_name_plural = 'نوتیف‌های بیرون پنل'
