from django.db import models
from simple_history.models import HistoricalRecords


class DustCost(models.Model):
    history = HistoricalRecords()

    created = models.DateTimeField(auto_now_add=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    amount = models.PositiveIntegerField()
    usdt_value = models.PositiveIntegerField()
    network = models.CharField(max_length=16)
    coin = models.CharField(max_length=16)

    @staticmethod
    def update_dust(start, end, amount: int, usdt_value: int, network: str, coin: str):
        dust_cost, _ = DustCost.objects.get_or_create(network=network, coin=coin)

        dust_cost.start = start
        dust_cost.end = end
        dust_cost.amount = amount
        dust_cost.usdt_value = usdt_value
        dust_cost.save()


