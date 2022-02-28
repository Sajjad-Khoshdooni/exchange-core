import uuid

from django.db import models


class FinotechRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    track_id = models.UUIDField(
        default=uuid.uuid4,
    )

    search_key = models.CharField(max_length=128, db_index=True, null=True, blank=True)

    url = models.CharField(max_length=256)
    data = models.JSONField(blank=True, null=True)
    method = models.CharField(max_length=8)

    status_code = models.PositiveSmallIntegerField(default=0)
    response = models.JSONField(blank=True, null=True)

    user = models.ForeignKey(to='accounts.User', on_delete=models.CASCADE)
