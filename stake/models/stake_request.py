import uuid
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Account
from accounts.utils import email
from ledger.models import Wallet, Trx
from ledger.utils.fields import get_group_id_field
from ledger.utils.wallet_pipeline import WalletPipeline
from stake.models import StakeOption
from stake.utils import change_status


class StakeRequest(models.Model):

    PROCESS, PENDING, DONE = 'process', 'pending', ' done'
    CANCEL_PROCESS, CANCEL_PENDING, CANCEL_COMPLETE = 'cancel_process', 'cancel_pending', 'cancel_complete'

    status_choice = ((PROCESS, PROCESS), (PENDING, PENDING), (DONE, DONE), (CANCEL_PROCESS, CANCEL_PROCESS),
                     (CANCEL_PENDING, CANCEL_PENDING), (CANCEL_COMPLETE, CANCEL_COMPLETE))

    status = models.CharField(choices=status_choice, max_length=16, default=PROCESS)

    stake_option = models.ForeignKey(StakeOption, on_delete=models.CASCADE)

    amount = models.PositiveIntegerField()

    group_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    def __str__(self):
        return self.stake_option.asset.symbol

    def save(self, *args, **kwargs):
        old = self.id and StakeRequest.objects.get(id=self.id)
        asset = self.stake_option.asset
        account = self.account
        spot_wallet = asset.get_wallet(account)
        stake_wallet = asset.get_wallet(account=account, market=Wallet.STAKE)
        user_email = account.user.email

        if old and old.status == StakeRequest.PROCESS and self.status == StakeRequest.CANCEL_PROCESS:

            with WalletPipeline() as pipeline:
                pipeline.new_trx(
                    group_id=self.group_id,
                    sender=stake_wallet,
                    receiver=spot_wallet,
                    amount=self.amount,
                    scope=Trx.STAKE
                )
                self.status = change_status(old.status, StakeRequest.CANCEL_COMPLETE)
            if user_email:
                email.send_email_by_template(
                    recipient=user_email,
                    template=email.SCOPE_CANCEL_STAKE,
                    context={'asset': self.stake_option.asset.name_fa, 'amount': self.amount},
                )

        super(StakeRequest, self).save(*args, **kwargs)

    def clean(self):
        old = self.id and StakeRequest.objects.get(id=self.id)
        asset = self.stake_option.asset
        account = self.account
        spot_wallet = asset.get_wallet(account)
        stake_wallet = asset.get_wallet(account=account, market=Wallet.STAKE)

        self.status = change_status(old.status, self.status)

        if old and old.status == StakeRequest.CANCEL_PENDING and self.status == StakeRequest.CANCEL_COMPLETE:
            with WalletPipeline() as pipeline:
                pipeline.new_trx(
                    group_id=self.group_id,
                    sender=stake_wallet,
                    receiver=spot_wallet,
                    amount=self.amount,
                    scope=Trx.STAKE
                )
            if account.user.email:
                email.send_email_by_template(
                    recipient=account.user.email,
                    template=email.SCOPE_CANCEL_STAKE,
                    context={'asset': self.stake_option.asset.name_fa, 'amount': self.amount},
                )
        if old and old.status == StakeRequest.PENDING and self.status == StakeRequest.DONE:
            if account.user.email:
                email.send_email_by_template(
                    recipient=account.user.email,
                    template=email.SCOPE_DONE_STAKE,
                    context={'asset': self.stake_option.asset.name_fa, 'amount': self.amount},
                )
