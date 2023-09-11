from django.db import models


class SystemConfig(models.Model):
    active = models.BooleanField()
    is_consultation_available = models.BooleanField(default=False)

    @classmethod
    def get_system_config(cls) -> 'SystemConfig':
        return SystemConfig.objects.filter(
            active=True
        ).first() or SystemConfig()
