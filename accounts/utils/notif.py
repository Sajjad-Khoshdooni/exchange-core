from uuid import UUID

from django.template import loader
from django.utils import timezone

from accounts.models.email_notification import EmailNotification
from accounts.utils import validation


def send_one_time_notification(users, group_id: UUID):
    pass


def send_2fa_activation_message(user):
    title = "فعال شدن تایید دو مرحله‌ای"
    context = {
        'now': validation.gregorian_to_jalali_datetime_str(timezone.now()),
        'name': f'{user.first_name} {user.last_name}'
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
    context = {
        'now': validation.gregorian_to_jalali_datetime_str(timezone.now()),
        'name': f'{user.first_name} {user.last_name}'
    }
    content_html = loader.render_to_string(
        'accounts/notif/email/2fa_deactivation_message.html',
        context=context)
    content = loader.render_to_string(
        'accounts/notif/email/2fa_deactivation_message.txt',
        context=context)

    EmailNotification.objects.create(recipient=user, title=title, content=content, content_html=content_html)
