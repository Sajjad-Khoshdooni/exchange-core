from django.conf import settings
from django.db import models
from accounts.models import User
from accounts.utils.validation import PHONE_MAX_LENGTH


class ExternalNotification(models.Model):

    SCOPE_LEVEL_2_PRIZE = 'level_2_prize'
    SCOPE_FIRST_FIAT_DEPOSIT_PRIZE = 'first_deposit_prize'
    TOKEN = 'پنجاه هزار شیبا'

    SCOPE_CHOICES = (
        (SCOPE_LEVEL_2_PRIZE, SCOPE_LEVEL_2_PRIZE),
        (SCOPE_FIRST_FIAT_DEPOSIT_PRIZE, SCOPE_FIRST_FIAT_DEPOSIT_PRIZE)
    )

    created = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(
        max_length=PHONE_MAX_LENGTH,
        verbose_name='شماره تماس',
        db_index=True
    )
    scope = models.CharField(
        max_length=22,
        choices=SCOPE_CHOICES
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    @classmethod
    def send_sms(cls, user: User, scope: str, ):
        from accounts.tasks import send_message_by_kavenegar
        ExternalNotification.objects.create(phone=user.phone, scope=scope, user=user)
        token = cls.TOKEN
        if scope == cls.SCOPE_LEVEL_2_PRIZE:
            template = 'ret-level2-verify'

        elif scope == cls.SCOPE_FIRST_FIAT_DEPOSIT_PRIZE:
            template = 'ret-first-fiat-deposit'
        else:
            raise NotImplementedError

        if settings.DEBUG_OR_TESTING:
            print('template={},phone={},token={}'.format(template, user.phone, token))
            return

        send_message_by_kavenegar(
            phone=user.phone,
            token=token,
            template=template
        )

    @staticmethod
    def get_users_sent_sms_notif(scope: str):
        users_id = ExternalNotification.objects.filter(scope=scope).values_list('user_id')
        return users_id