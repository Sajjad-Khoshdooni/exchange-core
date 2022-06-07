from django.db import models


class BinanceRequests(models.Model):
    WITHDRAW = 'withdraw'

    SCOPE_CHOICE = ((WITHDRAW, WITHDRAW),)

    scope = models.CharField(max_length=16, choices=SCOPE_CHOICE)
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    coin = models.CharField(max_length=32, blank=True)
    network = models.CharField(max_length=16, blank=True)
    address = models.CharField(max_length=256, blank=True)
    amount = models.FloatField(blank=True)
    caller_id = models.CharField(max_length=64, blank=True)
    status = models.CharField()

