from celery import shared_task
from django.db import transaction

from accounts.models import Notification, BulkNotification, User
from accounts.utils.push_notif import send_push_notif_to_user
from ledger.utils.fields import PENDING, DONE


@shared_task(queue='celery')
def send_notifications_push():
    # todo: handle concurrency

    for notif in Notification.objects.filter(push_status=Notification.PUSH_WAITING):
        send_push_notif_to_user(
            user=notif.recipient,
            title=notif.title,
            body=notif.message,
            image=notif.image,
            link=notif.link
        )

        notif.push_status = Notification.PUSH_SENT
        notif.save(update_fields=['push_status'])


@shared_task(queue='celery')
def process_bulk_notifications():
    with transaction.atomic():
        for bulk_notif in BulkNotification.objects.filter(status=PENDING).select_for_update():
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
