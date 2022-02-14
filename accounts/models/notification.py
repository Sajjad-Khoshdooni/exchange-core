from django.db import models
from django.utils import timezone


class Notification(models.Model):
    INFO, SUCCESS, WARNING, ERROR = 'info', 'success', 'warning', 'error'

    created = models.DateTimeField(auto_now_add=True)
    read_date = models.DateTimeField(null=True, blank=True)

    recipient = models.ForeignKey(to='accounts.User', on_delete=models.CASCADE)

    message = models.CharField(max_length=512)

    level = models.CharField(
        max_length=8,
        choices=((INFO, INFO), (SUCCESS, SUCCESS), (WARNING, WARNING), (ERROR, ERROR)),
        default=INFO
    )

    read = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created', )

    @classmethod
    def send(cls, recipient, message: str, level: str = INFO):
        Notification.objects.create(
            recipient=recipient,
            message=message,
            level=level
        )

    def make_read(self):
        if not self.read:
            self.read = True
            self.read_date = timezone.now()
            self.save()
