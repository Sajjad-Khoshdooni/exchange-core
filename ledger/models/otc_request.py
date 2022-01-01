from django.db import models

from accounts.models import Account
from ledger.models import Wallet, Asset, Order
from ledger.utils.fields import get_amount_field
from ledger.utils.random import secure_uuid4


class OTCRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    token = models.UUIDField(default=secure_uuid4, db_index=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)
    src_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='src_otc')
    dest_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='dest_otc')
    price = get_amount_field()
