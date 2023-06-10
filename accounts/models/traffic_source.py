import uuid

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.event.producer import get_kafka_producer
from accounts.models import User
from accounts.utils.dto import TrafficSourceEvent


class TrafficSource(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='کاربر')

    utm_source = models.CharField(max_length=256)
    utm_medium = models.CharField(max_length=256)
    utm_campaign = models.CharField(max_length=256)
    utm_content = models.CharField(max_length=256)
    utm_term = models.CharField(max_length=256)
    gps_adid = models.CharField(max_length=256)

    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)

    class Meta:
        verbose_name_plural = verbose_name = "منشا ترافیک"
        permissions = [
            ("has_marketing_adivery_reports", "Can read yektanet mobile analytics"),
            ("has_marketing_mediaad_reports", "Can read mediaad analytics"),
        ]

    def __str__(self):
        return 'نظرهای ' + str(self.user)


@receiver(post_save, sender=TrafficSource)
def handle_traffic_source_save(sender, instance, created, **kwargs):
    producer = get_kafka_producer()
    event = TrafficSourceEvent(
        created=instance.created,
        user_id=instance.user_id,
        event_id=uuid.uuid5(uuid.NAMESPACE_URL, str(instance.id) + TrafficSourceEvent.type),
        utm_source=instance.utm_source,
        utm_medium=instance.utm_medium,
        utm_campaign=instance.utm_campaign,
        utm_content=instance.utm_content,
        utm_term=instance.utm_term,
    )
    producer.produce(event)
