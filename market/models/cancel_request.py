from django.db import models

from market.models import Order


class CancelRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    order_id = models.PositiveIntegerField(unique=True)
