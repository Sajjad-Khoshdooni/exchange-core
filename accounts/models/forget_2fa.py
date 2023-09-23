from django.db import models, transaction
from django.template.loader import render_to_string
from django.conf import settings

from datetime import timedelta

from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models.sms_notification import SmsNotification
from accounts.models import User
from ledger.utils.fields import PENDING, get_status_field, CANCELED, DONE


class Forget2FA(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    status = get_status_field()

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    selfie_image = models.OneToOneField(
        to='multimedia.Image',
        on_delete=models.PROTECT,
        verbose_name='عکس سلفی',
        related_name='+',
        blank=True,
        null=True
    )

    def accept(self):
        assert self.status == PENDING

        user = self.user
        context = {
            'brand': settings.BRAND
        }

        content = render_to_string('accounts/notif/sms/2fa_forget_success', context=context)

        with transaction.atomic():
            SmsNotification.objects.create(
                recipient=user,
                content=content
            )

            self.status = DONE
            self.save(update_fields=['status'])

            TOTPDevice.objects.filter(user=user).update(confirmed=False)
            user.suspend(duration=timedelta(days=1))

    def reject(self):
        assert self.status == PENDING

        user = self.user
        context = {'brand': settings.BRAND}
        content = render_to_string('accounts/notif/sms/2fa_forget_reject', context=context)

        with transaction.atomic():

            SmsNotification.objects.create(
                recipient=user,
                content=content
            )

            self.status = CANCELED
            self.save(update_fields=['status'])

    class Meta:
        verbose_name = 'درخواست فراموشی شناسه دوعاملی'
        verbose_name_plural = 'درخواست‌های فراموشی شناسه دوعاملی'
