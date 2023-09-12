from django.db import models
from django.template.loader import render_to_string

from datetime import timedelta

from accounts.models import User
from accounts.tasks.send_sms import send_kavenegar_exclusive_sms


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

    def send_success_message(self):
        user = self.user
        user.suspend(duration=timedelta(days=1), reason='فراموشی شناسه دوعاملی')
        context = {}
        content = render_to_string('accounts/notif/sms/2fa_forget_success', context=context)
        send_kavenegar_exclusive_sms(
            phone=user.phone,
            content=content
        )

    def send_reject_message(self):
        user = self.user
        context = {}
        content = render_to_string('accounts/notif/sms/2fa_forget_reject', context=context)
        send_kavenegar_exclusive_sms(
            phone=user.phone,
            content=content
        )

    class Meta:
        verbose_name = 'درخواست فراموشی شناسه دوعاملی'
        verbose_name_plural = 'درخواست‌های فراموشی شناسه دوعاملی'
