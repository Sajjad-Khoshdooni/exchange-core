import logging

from django.db import models
from django.utils import timezone

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

    level = models.CharField(
        max_length=8,
        choices=LEVEL_CHOICES,
        default=INFO
    )

    read = models.BooleanField(default=False)

    push_status = models.CharField(
        choices=((PUSH_WAITING, 'waiting'), (PUSH_SENT, 'sent')),
        blank=True,
        max_length=1,
        db_index=True
    )

    class Meta:
        ordering = ('-created', )

    @classmethod
    def send(cls, recipient, title: str, link: str = '', message: str = '', level: str = INFO, send_push: bool = False):
        if not recipient:
            logger.info('failed to send notif')
            return

        Notification.objects.create(
            recipient=recipient,
            title=title,
            link=link,
            message=message,
            level=level,
            push_status=Notification.PUSH_WAITING if send_push else ''
        )

    def make_read(self):
        if not self.read:
            self.read = True
            self.read_date = timezone.now()
            self.save()
