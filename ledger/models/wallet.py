from django.db import models

from ledger.models import NetworkAsset
from ledger.utils.constants import AMOUNT_MAX_DIGITS, AMOUNT_DECIMAL_PLACES


class Wallet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    balance = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
