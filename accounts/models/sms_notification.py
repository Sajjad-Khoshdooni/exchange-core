import logging

from django.db import models

from ledger.utils.fields import get_group_id_field

logger = logging.getLogger(__name__)


class SmsNotification(models.Model):
    RECENT_SIGNUP_NOT_DEPOSITED = 'recent_not_deposit'
    WEEKLY_MISSION_ACTIVATED = 'weekly_mission_activated'

    created = models.DateTimeField(auto_now_add=True)

    recipient = models.ForeignKey(to='accounts.User', on_delete=models.CASCADE)

    template = models.CharField(max_length=32)
    params = models.JSONField(null=True, blank=True)
    sent = models.BooleanField(default=False, db_index=True)

    group_id = get_group_id_field(null=True, db_index=True, default=None)

    class Meta:
        ordering = ('-created', )
        unique_together = ('recipient', 'group_id')
        indexes = models.Index(fields=['recipient', 'template']),
