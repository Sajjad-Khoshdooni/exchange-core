from uuid import UUID
from django.utils import timezone
from django.template import loader

from accounts.models.user import User
from accounts.models.email_notification import EmailNotification
from accounts.utils import validation
from django.template import loader
from django.utils import timezone

from accounts.models.email_notification import EmailNotification
from accounts.utils import validation


def send_one_time_notification(users, group_id: UUID):
    pass
def send_successful_change_phone_email(user: User):
    title = "تغییر شماره همراه"
    is_spam = EmailNotification.objects.filter(recipient=user, title=title,
                                               created__gte=timezone.now() - timezone.timedelta(minutes=5)).exists()
    if not is_spam:
        context = {
            'now': validation.gregorian_to_jalali_datetime_str(timezone.now()),
        }
        content_html = loader.render_to_string(
            'accounts/notif/email/successful_change_phone.html',
            context=context)
        content = loader.render_to_string(
            'accounts/notif/email/successful_change_phone.txt',
            context=context)
        EmailNotification.objects.create(recipient=user, title=title, content=content, content_html=content_html)


def send_2fa_activation_message(user):
    title = "فعال شدن تایید دو مرحله‌ای"
    is_spam = EmailNotification.objects.filter(recipient=user, title=title,
                                               created__gte=timezone.now() - timezone.timedelta(minutes=5)).exists()
    if not is_spam:
        context = {
            'now': validation.gregorian_to_jalali_datetime_str(timezone.now())
        }
        content_html = loader.render_to_string(
            'accounts/notif/email/2fa_activation_message.html',
            context=context)
        content = loader.render_to_string(
            'accounts/notif/email/2fa_activation_message.txt',
            context=context)

        EmailNotification.objects.create(recipient=user, title=title, content=content, content_html=content_html)


def send_2fa_deactivation_message(user):
    title = "غیرفعال شدن تایید دو مرحله‌ای"
    is_spam = EmailNotification.objects.filter(recipient=user, title=title,
                                               created__gte=timezone.now() - timezone.timedelta(minutes=5)).exists()
    if not is_spam:
        context = {
            'now': validation.gregorian_to_jalali_datetime_str(timezone.now())
        }
        content_html = loader.render_to_string(
            'accounts/notif/email/2fa_deactivation_message.html',
            context=context)
        content = loader.render_to_string(
            'accounts/notif/email/2fa_deactivation_message.txt',
            context=context)

        EmailNotification.objects.create(recipient=user, title=title, content=content, content_html=content_html)
