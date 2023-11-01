from django.db import models

from accounts.models import User
from ledger.models import Asset, Network
from ledger.utils.fields import get_amount_field, get_address_field, get_status_field


class DepositRecoveryRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    status = get_status_field()
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    coin = models.ForeignKey(Asset, on_delete=models.PROTECT)
    network = models.ForeignKey(Network, on_delete=models.PROTECT)
    memo = models.CharField(max_length=64, blank=True)
    trx_hash = models.CharField(max_length=128, db_index=True, null=True, blank=True)
    amount = get_amount_field()
    address = get_address_field()
    description = models.TextField(blank=True)

    details_image = models.OneToOneField(
        to='multimedia.Image',
        on_delete=models.PROTECT,
        verbose_name='تصویر جزییات برداشت',
        related_name='+',
        blank=True,
        null=True
    )

    comment = models.TextField(blank=True)

    def accept(self):
        pass

    def reject(self):
        pass

    def refund(self):
        pass
