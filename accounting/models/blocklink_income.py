from django.db import models


class BlockLinkIncome(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    fee_amount = models.PositiveIntegerField()
    usdt_value = models.PositiveIntegerField()
    core_income = models.PositiveIntegerField()
    network = models.CharField(max_length=16, unique=True, db_index=True)
    coin = models.CharField(max_length=16, unique=True, db_index=True)

