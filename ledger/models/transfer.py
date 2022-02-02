from uuid import uuid4

from django.db import models

from accounts.models import Account
from ledger.models import Trx
from ledger.utils.fields import get_amount_field, get_address_field


class Transfer(models.Model):
    PENDING, CANCELED, REVERTED, DONE, NOT_BROADCAST = 'pending', 'canceled', 'reverted', 'done', 'not_brod'

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
        choices=[(NOT_BROADCAST, NOT_BROADCAST), (PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE, null=True, blank=True)

    trx_hash = models.CharField(max_length=128, db_index=True, unique=True, null=True, blank=True)
    block_hash = models.CharField(max_length=128, db_index=True, unique=True, blank=True, null=True)
    block_number = models.PositiveIntegerField(null=True, blank=True)

    out_address = get_address_field()

    def get_explorer_link(self) -> str:
        return self.network.explorer_link.format(hash=self.block_hash)

    def build_trx(self):
        if self.deposit:
            return Trx.objects.create(
                group_id=self.group_id,
                sender=self.wallet.asset.get_wallet(Account.out()),
                receiver=self.wallet,
                amount=self.amount,
                scope=Trx.TRANSFER
            )
        else:
            return Trx.objects.create(
                group_id=self.group_id,
                sender=self.wallet,
                receiver=self.wallet.asset.get_wallet(Account.out()),
                amount=self.amount,
                scope=Trx.TRANSFER
            )
