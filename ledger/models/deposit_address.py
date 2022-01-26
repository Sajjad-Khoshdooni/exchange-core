from django.db import models, transaction
from rest_framework import serializers

from ledger.utils.address import get_network_address


class DepositAddress(models.Model):
    schema = models.ForeignKey('ledger.AddressSchema', on_delete=models.PROTECT)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True, unique=True)
    # address_tag = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return '%s %s (schema= %s)' % (self.account, self.address, self.schema)

    def save(self, *args, **kwargs):

        if not self.pk:
            self.address = ''
            super().save(*args, **kwargs)
            self.address = get_network_address(self.schema.symbol.lower(), self.pk)
            self.save()

        else:
            super().save(*args, **kwargs)

    class Meta:
        unique_together = ('schema', 'account')
