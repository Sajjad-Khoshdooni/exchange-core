import uuid

from django.db import models


class FinotechRequest(models.Model):
    FINOTECH, JIBIT = 'finotech', 'jibit'

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    track_id = models.UUIDField(
        default=uuid.uuid4,
    )

    search_key = models.CharField(max_length=128, db_index=True, null=True, blank=True)

    service = models.CharField(max_length=8, choices=((FINOTECH, FINOTECH), (JIBIT, JIBIT)))

    url = models.CharField(max_length=256)
    data = models.JSONField(blank=True, null=True)
    method = models.CharField(max_length=8)

    status_code = models.PositiveSmallIntegerField(default=0, verbose_name='وضعیت')
    response = models.JSONField(blank=True, null=True)

    user = models.ForeignKey(to='accounts.User', on_delete=models.CASCADE, null=True, blank=True)
