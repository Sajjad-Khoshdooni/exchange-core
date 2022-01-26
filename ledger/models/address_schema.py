from django.db import models


class AddressSchema(models.Model):
    ETH = 'ETH'

    symbol = models.CharField(max_length=4, unique=True)

    def __str__(self):
        return self.symbol
