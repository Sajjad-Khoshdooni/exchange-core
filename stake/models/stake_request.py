import uuid
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models, transaction

from accounts.models import Account
from accounts.utils import email
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from ledger.models import Wallet, Trx
from ledger.utils.fields import get_group_id_field, get_amount_field
from ledger.utils.wallet_pipeline import WalletPipeline
from stake.models import StakeOption


class StakeRequest(models.Model):

    PROCESS, PENDING, DONE = 'process', 'pending', ' done'
    CANCEL_PROCESS, CANCEL_PENDING, CANCEL_COMPLETE = 'cancel_process', 'cancel_pending', 'cancel_complete'

    STATUS_CHOICE = ((PROCESS, PROCESS), (PENDING, PENDING), (DONE, DONE), (CANCEL_PROCESS, CANCEL_PROCESS),
                     (CANCEL_PENDING, CANCEL_PENDING), (CANCEL_COMPLETE, CANCEL_COMPLETE))

    status = models.CharField(choices=STATUS_CHOICE, max_length=16, default=PROCESS)

    stake_option = models.ForeignKey(StakeOption, on_delete=models.CASCADE)

    amount = get_amount_field()

    group_id = get_group_id_field()

    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    def __str__(self):
        return self.stake_option.__str__() + ' ' + str(self.account_id)

    def send_email_for_staking(self, user_email: str, template: str):
        if user_email:
            email.send_email_by_template(
                recipient=user_email,
                template=template,
                context={'asset': self.stake_option.asset.name_fa, 'amount': self.amount},
            )
        else:
            return

    def change_status(self, new_status: str):
        old_status = self.status
        account = self.account
        asset = self.stake_option.asset
        user_email = account.user.email
        valid_change_status = [
            (self.PROCESS, self.PENDING), (self.PROCESS, self.CANCEL_COMPLETE),
            (self.PENDING, self.DONE), (self.PENDING, self.CANCEL_PROCESS),
            (self.DONE, self.CANCEL_PROCESS), (self.CANCEL_PROCESS, self.CANCEL_PENDING),
            (self.CANCEL_PENDING, self.CANCEL_COMPLETE),
        ]
        valid_cancellation_status = [(self.PROCESS, self.CANCEL_COMPLETE), (self.CANCEL_PENDING, self.CANCEL_COMPLETE)]

        assert (old_status, new_status) in valid_change_status, 'invalid change_status'

        if (old_status, new_status) in valid_cancellation_status:
            spot_wallet = asset.get_wallet(account)
            stake_wallet = asset.get_wallet(account=account, market=Wallet.STAKE)
            with WalletPipeline() as pipeline:
                pipeline.new_trx(
                    group_id=self.group_id,
                    sender=stake_wallet,
                    receiver=spot_wallet,
                    amount=self.amount,
                    scope=Trx.STAKE
                )
                self.status = new_status
                self.save()
            self.send_email_for_staking(user_email=user_email, template=email.SCOPE_CANCEL_STAKE)

        elif (old_status, new_status) == (self.PENDING, self.DONE):
            self.status = new_status
            self.save()
            self.send_email_for_staking(user_email=user_email, template=email.SCOPE_DONE_STAKE)

        elif (old_status, new_status) in [(self.PENDING, self.CANCEL_PROCESS), (self.DONE, self.CANCEL_PROCESS)]:
            self.status = new_status
            self.save()
            link = url_to_edit_object(self)
            send_support_message(
                message='ثبت درخواست لغو staking برای {} {}'.format(self.stake_option.asset, self.amount, ),
                link=link
            )

        else:
            self.status = new_status
            self.save()


