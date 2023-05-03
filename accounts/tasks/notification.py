from celery import shared_task

from accounts.models import Notification
from accounts.utils.push_notif import send_push_notif_to_user


@shared_task(queue='celery')
def send_notifications_push():

    for notif in Notification.objects.filter(push_status=Notification.PUSH_WAITING):
        send_push_notif_to_user(
            user=notif.recipient,
            title=notif.title,
            body=notif.message,
            link=notif.link
        )
