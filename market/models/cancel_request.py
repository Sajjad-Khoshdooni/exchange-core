from django.db import models

from market.models import Order


class CancelRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='cancel_request')
    order_status = models.CharField(max_length=8)