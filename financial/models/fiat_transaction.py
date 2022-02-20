from django.db import models, transaction

from accounts.models import Account
from ledger.models import Trx, Asset
from ledger.utils.fields import get_status_field, DONE, get_group_id_field


class FiatTransaction(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    account = models.ForeignKey(to=Account, on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()

    deposit = models.BooleanField(default=False)

    status = get_status_field()

    def save(self, *args, **kwargs):
        old = self.id and FiatTransaction.objects.get(id=self.id)

        if old and old.status == DONE and self.status != DONE:
            return

        with transaction.atomic():
            super(FiatTransaction, self).save(*args, **kwargs)

            if (not old or old.status != DONE) and self.status == DONE:
                asset = Asset.get(Asset.IRT)

                sender, receiver = asset.get_wallet(Account.out()), asset.get_wallet(self.account)

                if not self.deposit:
                    sender, receiver = receiver, sender

                Trx.transaction(
                    sender=sender,
                    receiver=receiver,
                    group_id=self.group_id,
                    scope=Trx.TRANSFER,
                    amount=self.amount
                )