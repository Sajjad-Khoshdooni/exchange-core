import logging

from django.db import models
from django.utils import timezone

from ledger.utils.fields import get_group_id_field, get_status_field

logger = logging.getLogger(__name__)


class Notification(models.Model):
    INFO, SUCCESS, WARNING, ERROR = 'info', 'success', 'warning', 'error'
    LEVEL_CHOICES = ((INFO, INFO), (SUCCESS, SUCCESS), (WARNING, WARNING), (ERROR, ERROR))

    PUSH_WAITING, PUSH_SENT = 'w', 's'

    created = models.DateTimeField(auto_now_add=True)
    read_date = models.DateTimeField(null=True, blank=True)

    recipient = models.ForeignKey(to='accounts.User', on_delete=models.CASCADE)

    title = models.CharField(max_length=128)
    link = models.CharField(blank=True, max_length=128)
    message = models.CharField(max_length=512, blank=True)

    image = models.URLField(blank=True)

    level = models.CharField(
        max_length=8,
        choices=LEVEL_CHOICES,
        default=INFO
    )

    read = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    push_status = models.CharField(
        choices=((PUSH_WAITING, 'waiting'), (PUSH_SENT, 'sent')),
        blank=True,
        max_length=1,
        db_index=True
    )

    group_id = get_group_id_field(null=True, db_index=True, default=None)

    class Meta:
        ordering = ('-created', )
        unique_together = ('recipient', 'group_id')
        indexes = [
            models.Index(fields=['recipient', 'read', 'hidden'], name="notification_idx")
        ]

    @classmethod
    def send(cls, recipient, title: str, link: str = '', message: str = '', level: str = INFO, image: str = '',
             send_push: bool = True):

        if not recipient:
            logger.info('failed to send notif')
            return

        return Notification.objects.create(
            recipient=recipient,
            title=title,
            link=link,
            message=message,
            level=level,
            image=image,
            push_status=Notification.PUSH_WAITING if send_push else ''
        )

    def make_read(self):
        if not self.read:
            self.read = True
            self.read_date = timezone.now()
            self.save()


class BulkNotification(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()
    status = get_status_field()

    title = models.CharField(max_length=128)
    link = models.CharField(blank=True, max_length=128)
    message = models.TextField(blank=True)

    level = models.CharField(
        max_length=8,
        choices=Notification.LEVEL_CHOICES,
        default=Notification.INFO
    )
