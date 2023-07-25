import logging

from django.db import models
from django.db.models import UniqueConstraint, Q, Sum
from django.utils import timezone

from ledger.utils.fields import get_group_id_field, get_status_field

logger = logging.getLogger(__name__)


class LiveNotification(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(read=False)


class Notification(models.Model):
    INFO, SUCCESS, WARNING, ERROR = 'info', 'success', 'warning', 'error'
    LEVEL_CHOICES = ((INFO, INFO), (SUCCESS, SUCCESS), (WARNING, WARNING), (ERROR, ERROR))

    PUSH_WAITING, PUSH_SENT = 'w', 's'

    RAASTIN, NINJA = 'raastin', 'ninja'
    SOURCE_CHOICE = ((RAASTIN, RAASTIN), (NINJA, NINJA))

    LIKE, COMMENT, FOLLOW, SYSTEM = 'like', 'comment', 'follow', 'system'
    TARGET_SOURCE = ((LIKE, LIKE), (COMMENT, COMMENT), (FOLLOW, FOLLOW), (SYSTEM, SYSTEM))

    ORDINARY, REPLACEABLE, DIFF = 'ord', 'rep', 'dif'
    TYPE_CHOICE = ((ORDINARY, ORDINARY), (REPLACEABLE, REPLACEABLE), (DIFF, DIFF))

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

    source = models.CharField(
        max_length=8,
        choices=SOURCE_CHOICE,
        default=RAASTIN
    )
    type = models.CharField(
        max_length=3,
        choices=TYPE_CHOICE,
        default=ORDINARY
    )
    target = models.CharField(
        max_length=8,
        choices=TARGET_SOURCE,
        default=SYSTEM
    )
    count = models.IntegerField(default=0, null=True, blank=True)
    template = models.ForeignKey('accounts.Template', on_delete=models.CASCADE)

    objects = models.Manager()
    live_objects = LiveNotification()

    class Meta:
        ordering = ('-created', )
        indexes = [
            models.Index(fields=['recipient', 'read', 'hidden'], name="notification_idx")
        ]

        constraints = [
            UniqueConstraint(
                name='unique_unread_group_id',
                fields=["group_id", "target"],
                condition=Q(read=False) & Q(source='ninja')
            ),
            UniqueConstraint(
                name='unique_recipient_group_id',
                fields=['recipient', 'group_id'],
                condition=Q(target='system')
            )
        ]

    @classmethod
    def send(cls, recipient, title: str, link: str = '', message: str = '', level: str = INFO, image: str = '',
             send_push: bool = True, group_id=None, type: str = ORDINARY, target: str = SYSTEM, source: str = RAASTIN,
             count: int = 1):
        from accounts.models import Template

        if not recipient:
            logger.info('failed to send notif')
            return

        template = Template.objects.get(target=target)

        if type == cls.ORDINARY:
            if Notification.live_objects.filter(group_id=group_id, source=cls.NINJA).exists():
                return

            notification = Notification.objects.get_or_create(
                group_id=group_id,
                defaults={
                    'target': target,
                    'title': title,
                    'link': link,
                    'message': message,
                    'level': level,
                    'source': source,
                    'image': image,
                    'type': type,
                    'template': template,
                    'count': count,
                    'push_status': Notification.PUSH_WAITING if send_push else '',
                    'recipient': recipient
                }
            )
        elif not group_id:
            logger.info('failed to send notif, uuid error')
            return

        elif type == cls.REPLACEABLE:
            notification, _ = Notification.objects.update_or_create(
                group_id=group_id,
                target=target,
                defaults={
                    'title': title,
                    'link': link,
                    'message': message,
                    'image': image,
                    'count': count,
                    'source': source,
                    'type': type,
                    'template': template,
                    'level': level,
                    'recipient': recipient
                }
            )
        elif type == cls.DIFF:
            read_count = Notification.objects.filter(group_id=group_id, read=True).aggregate(Sum('count'))[
                'count__sum']
            if read_count:
                count = max(count - read_count, 1)

            notification, _ = Notification.objects.update_or_create(
                group_id=group_id,
                target=target,
                defaults={
                    'title': title,
                    'link': link,
                    'message': message,
                    'image': image,
                    'count': count,
                    'source': source,
                    'type': type,
                    'template': template,
                    'level': level,
                    'recipient': recipient
                }
            )
        else:
            logger.info('failed to send notif')
            return

        return notification

    @property
    def content(self):
        return str(self.template.content).format(last=self.message, count=self.count)

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
