from django.db import models


class AppStatus(models.Model):

    active = models.BooleanField(default=True, unique=True)

    latest_version = models.PositiveIntegerField(default=1)
    force_update_version = models.PositiveIntegerField(default=0)

    @classmethod
    def get_active(cls) -> 'AppStatus':
        return AppStatus.objects.filter(active=True).first() or AppStatus()

    class Meta:
        verbose_name = verbose_name_plural = 'وضعیت اپلیکیشن'
