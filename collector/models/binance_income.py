from django.db import models

from ledger.utils.fields import get_created_field, get_amount_field


class BinanceIncome(models.Model):
    created = get_created_field()

    symbol = models.CharField(max_length=64)
    income_type = models.CharField(max_length=64)
    tran_id = models.CharField(max_length=32, db_index=True, unique=True)
    income = get_amount_field()
    asset = models.CharField(max_length=32)
    income_date = models.DateTimeField()
