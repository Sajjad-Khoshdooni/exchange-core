from django.db import models

ARCHITECTURE_OF_NETWORK = {
    'ETH': 'ETH',
    'BSC': 'ETH',
    'TRX': 'TRX',
    'BTC': 'BTC',
    'SOL': 'SOL'
}


class AddressKey(models.Model):
    account = models.ForeignKey('accounts.account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256)  # pointer_address
    public_address = models.CharField(max_length=256)
    architecture = models.CharField(max_length=16)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('account', 'address')

    def __str__(self):
        return self.address
