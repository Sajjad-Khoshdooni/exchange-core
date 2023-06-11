from celery import shared_task
from django.template.loader import render_to_string

from accounts.models import Notification, BulkNotification, User, EmailNotification
from accounts.models.sms_notification import SmsNotification
from accounts.tasks.send_sms import send_kavenegar_exclusive_sms
from accounts.utils.email import send_email
from accounts.utils.push_notif import send_push_notif_to_user
from ledger.utils.fields import PENDING, DONE


@shared_task(queue='notif-manager')
def send_notifications_push():
    for notif in Notification.objects.filter(push_status=Notification.PUSH_WAITING).order_by('id')[:100]:
        send_push_notif_to_user(
            user=notif.recipient,
            title=notif.title,
            body=notif.message,
            image=notif.image,
            link=notif.link
        )

        notif.push_status = Notification.PUSH_SENT
        notif.save(update_fields=['push_status'])


@shared_task(queue='notif-manager')
def process_bulk_notifications():
    for bulk_notif in BulkNotification.objects.filter(status=PENDING):
        sent_users = list(Notification.objects.filter(group_id=bulk_notif.group_id).values_list('recipient', flat=True))

        notifs = []

        for u in User.objects.exclude(id__in=sent_users):
            notifs.append(
                Notification(
                    recipient=u,
                    group_id=bulk_notif.group_id,
                    title=bulk_notif.title,
                    message=bulk_notif.message,
                    link=bulk_notif.link,
                    level=bulk_notif.level,
                    push_status=Notification.PUSH_WAITING
                )
            )

            if len(notifs) > 1000:
                Notification.objects.bulk_create(notifs)
                notifs = []

        if notifs:
            Notification.objects.bulk_create(notifs)

        bulk_notif.status = DONE
        bulk_notif.save(update_fields=['status'])


@shared_task(queue='notif-manager')
def send_sms_notifications():
    for notif in SmsNotification.objects.filter(sent=False).order_by('id')[:100]:

        resp = send_kavenegar_exclusive_sms(
            phone=notif.recipient.phone,
            template=notif.template,
            params=notif.params,
            content=notif.content
        )

        if resp:
            notif.sent = True
            notif.save(update_fields=['sent'])


@shared_task(queue='notif-manager')
def send_email_notifications():
    for email_notif in EmailNotification.objects.filter(sent=False):

        resp = send_email(
            subject=email_notif.title,
            body_html=render_to_string('accounts/email/template_email.html', email_notif.context),
            body_text=render_to_string(email_notif.content, {}),
            to=[email_notif.user.email]
        )
        if resp:
            email_notif.sent = True
            email_notif.save(update_fields=['sent'])

