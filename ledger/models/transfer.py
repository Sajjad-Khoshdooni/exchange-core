from uuid import uuid4

from django.db import models

from ledger.utils.fields import get_amount_field, get_address_field


class Transfer(models.Model):
    PENDING, CANCELED, REVERTED, DONE = 'pending', 'canceled', 'reverted', 'done'

    created = models.DateTimeField(auto_now_add=True)
    group_id = models.UUIDField(default=uuid4, db_index=True)
    deposit_address = models.ForeignKey('ledger.DepositAddress', on_delete=models.CASCADE, null=True, blank=True)
    network = models.ForeignKey('ledger.Network', on_delete=models.CASCADE)
    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)

    amount = get_amount_field()
    deposit = models.BooleanField()

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE, null=True, blank=True)

    trx_hash = models.CharField(max_length=128, db_index=True, unique=True, null=True, blank=True)
    block_hash = models.CharField(max_length=128, db_index=True, unique=True, blank=True, null=True)
    block_number = models.PositiveIntegerField(null=True, blank=True)

    out_address = get_address_field()

    def get_explorer_link(self) -> str:
        return self.network.explorer_link.format(hash=self.block_hash)
