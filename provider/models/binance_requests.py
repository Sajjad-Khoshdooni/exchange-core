from django.db import models

from ledger.utils.fields import get_amount_field


class BinanceRequests(models.Model):

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    status_code = models.PositiveSmallIntegerField(default=0, verbose_name='وضعیت')
    url = models.CharField(max_length=256)
    data = models.JSONField(blank=True, null=True)
    method = models.CharField(max_length=8)
    response = models.JSONField(blank=True, null=True)


class BinanceTransferHistory(models.Model):

    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'
    WITHDRAW, DEPOSIT = 'withdraw', 'deposit'

    tx_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
    binance_id = models.CharField(max_length=128, unique=True, null=True, blank=True)

    address = models.CharField(max_length=256)
    amount = get_amount_field()
    coin = models.CharField(max_length=16)
    date = models.DateTimeField()
    network = models.CharField(max_length=16)
    status = models.CharField(max_length=16, choices=((PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)))
    type = models.CharField(max_length=16, choices=((WITHDRAW, WITHDRAW), (DEPOSIT, DEPOSIT)))

    def __str__(self):
        return self.type + ' ' + self.coin


class BinanceWallet(models.Model):
    SPOT, FUTURES = 'spot', 'futures'
    asset = models.CharField(max_length=16)
    free = get_amount_field()
    locked = get_amount_field()
    type = models.CharField(max_length=16, choices=((SPOT, SPOT), (FUTURES, FUTURES)))

    class Meta:
        unique_together = [('asset', 'type')]

    def __str__(self):
        return self.asset + ' ' + self.type




