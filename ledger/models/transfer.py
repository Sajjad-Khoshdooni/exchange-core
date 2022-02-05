import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models

from accounts.models import Account
from ledger.models import Trx
from ledger.models import Wallet, Network
from ledger.utils.fields import get_amount_field, get_address_field

logger = logging.getLogger(__name__)


class Transfer(models.Model):
    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done',
    SELF, BINANCE = 'self', 'binance'

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
        choices=[(PROCESSING, PROCESSING), (PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE, null=True, blank=True)

    trx_hash = models.CharField(max_length=128, db_index=True, unique=True, null=True)
    block_hash = models.CharField(max_length=128, db_index=True, unique=True, null=True)
    block_number = models.PositiveIntegerField(null=True)

    out_address = get_address_field()

    is_fee = models.BooleanField(default=False)

    source = models.CharField(max_length=8, default=BINANCE, choices=((SELF, SELF), (BINANCE, BINANCE)))
    provider_transfer = models.OneToOneField(to='provider.ProviderTransfer', on_delete=models.PROTECT, null=True, blank=True)
    handling = models.BooleanField(default=False)

    def get_explorer_link(self) -> str:
        return self.network.explorer_link.format(hash=self.block_hash)

    def build_trx(self):
        if self.deposit and self.is_fee:
            logger.info(f'Creating Trx for transfer id: {self.id} ignored.')
            return None

        elif self.deposit:
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

    @classmethod
    def new_withdraw(cls, wallet: Wallet, network: Network, amount: Decimal, address: str):
        lock = wallet.lock_balance(amount)
        deposit_address = network.get_deposit_address(wallet.account)

        transfer = Transfer.objects.create(
            wallet=wallet,
            network=network,
            amount=amount,
            lock=lock,
            deposit_address=deposit_address,
            out_address=address,
            deposit=False
        )

        return transfer
