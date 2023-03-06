from django.db import models


class BlockLinkIncome(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    start = models.DateTimeField(unique=True)
    real_fee_amount = models.PositiveIntegerField()
    fee_cost = models.PositiveIntegerField()
    fee_income = models.PositiveIntegerField()
    network = models.CharField(max_length=16)
    coin = models.CharField(max_length=16)

