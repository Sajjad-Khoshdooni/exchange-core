from django.db import models, transaction

from accounts.models import User
from ledger.models import Asset, Network, Transfer
from ledger.utils.fields import get_amount_field, get_address_field, get_status_field, PROCESS, CANCELED, DONE
from ledger.utils.price import get_last_price


class DepositRecoveryRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    status = get_status_field()
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    coin = models.ForeignKey(Asset, on_delete=models.PROTECT)
    network = models.ForeignKey(Network, on_delete=models.PROTECT)
    memo = models.CharField(max_length=64, blank=True)
    trx_hash = models.CharField(max_length=128)
    amount = get_amount_field()
    receiver_address = get_address_field()
    sender_address = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)

    details_image = models.OneToOneField(
        to='multimedia.Image',
        on_delete=models.PROTECT,
        verbose_name='تصویر جزییات برداشت',
        related_name='+',
        blank=True,
        null=True
    )

    comment = models.TextField(blank=True)

    def accept(self):
        self.status = PROCESS
        self.save(update_fields=['status'])

    def reject(self):
        self.status = CANCELED
        self.save(update_fields=['status'])

    def create_transfer(self):
        with transaction.atomic():
            self.status = DONE
            self.save(update_fields=['status'])
            wallet = self.coin.get_wallet(account=self.user.get_account())
            price_usdt = get_last_price(wallet.asset.symbol + Asset.USDT) or 0
            price_irt = get_last_price(wallet.asset.symbol + Asset.IRT) or 0
            trx = Transfer.objects.create(
                network=self.network,
                memo=self.memo,
                amount=self.amount,
                wallet=wallet,
                source=Transfer.MANUAL,
                out_address=self.sender_address,
                deposit=True,
                price_usdt=self.amount * price_usdt,
                price_irt=self.amount * price_irt
            )
            trx.accept(tx_id=self.trx_hash)
