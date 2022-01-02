from uuid import uuid4

from django.db import models

from ledger.utils.fields import get_amount_field


class Trx(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='received_trx')
    amount = get_amount_field()

    group_id = models.UUIDField(default=uuid4, db_index=True)

    def save(self, *args, **kwargs):
        assert self.sender.asset == self.receiver.asset
        assert self.sender != self.receiver

        return super(Trx, self).save(*args, **kwargs)
