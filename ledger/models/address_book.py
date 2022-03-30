from django.db import models
from .asset import Asset
from .network import Network
from accounts.models import Account


class AddressBook(models.Model):

    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)
    network = models.ForeignKey(to=Network, on_delete=models.CASCADE)
    asset = models.ForeignKey(to=Asset, blank=True, null=True, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name
