from django.db import models


class AddressKey(models.Model):
    account = models.ForeignKey('accounts.account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('account', 'address')
