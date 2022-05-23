from django.db import models

from ledger.models import Asset


class CoinCategory(models.Model):
    name = models.CharField(max_length=30)
    name_fa = models.CharField(max_length=30, blank=True, null=True)
    coin = models.ManyToManyField(Asset, null=True, blank=True)

    class Meta:
        verbose_name_plural = verbose_name = 'دسته بندی رمزارزها'

    def __str__(self):
        return self.name
