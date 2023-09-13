from django.db import models
from django.template.loader import render_to_string
from django.conf import settings

from datetime import timedelta

from accounts.models.sms_notification import SmsNotification
from accounts.models import User


class Forget2FA(models.Model):
    PENDING, REJECTED, ACCEPTED = ['pending', 'rejected', 'accepted']

    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=[
        (PENDING, PENDING),
        (ACCEPTED, ACCEPTED),
        (REJECTED, REJECTED)
        ],
        max_length=15,
        default=PENDING
    )
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
        user = self.user
        user.suspend(duration=timedelta(days=1), reason='فراموشی شناسه دوعاملی')
        context = {'brand': settings.BRAND}
        content = render_to_string('accounts/notif/sms/2fa_forget_success', context=context)
        SmsNotification.objects.create(
            recipient=user,
            content=content
        )

    def reject(self):
        user = self.user
        context = {'brand': settings.BRAND}
        content = render_to_string('accounts/notif/sms/2fa_forget_reject', context=context)
        SmsNotification.objects.create(
            recipient=user,
            content=content
        )

    class Meta:
        verbose_name = 'درخواست فراموشی شناسه دوعاملی'
        verbose_name_plural = 'درخواست‌های فراموشی شناسه دوعاملی'
