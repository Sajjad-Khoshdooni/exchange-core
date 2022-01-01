from django.db import models

from ledger.models import NetworkAsset
from ledger.utils.fields import AMOUNT_MAX_DIGITS, AMOUNT_DECIMAL_PLACES, get_amount_field


class Wallet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey('account.Account', on_delete=models.PROTECT)
    balance = get_amount_field()
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
