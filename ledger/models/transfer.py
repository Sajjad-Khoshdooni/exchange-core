import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models
from django.db.models import UniqueConstraint, Q

from accounts.models import Account
from ledger.consts import DEFAULT_COIN_OF_NETWORK
from ledger.models import Trx, NetworkAsset, Asset, DepositAddress
from ledger.models import Wallet, Network
from ledger.models.crypto_balance import CryptoBalance
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
    fee_amount = get_amount_field(default=Decimal(0))

    deposit = models.BooleanField()

    status = models.CharField(
        default=PROCESSING,
        max_length=8,
        choices=[(PROCESSING, PROCESSING), (PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE, null=True, blank=True)

    trx_hash = models.CharField(max_length=128, db_index=True, blank=True)
    block_hash = models.CharField(max_length=128, db_index=True, blank=True)
    block_number = models.PositiveIntegerField(null=True, blank=True)

    out_address = get_address_field()

    is_fee = models.BooleanField(default=False)

    source = models.CharField(max_length=8, default=SELF, choices=((SELF, SELF), (BINANCE, BINANCE)))
    provider_transfer = models.OneToOneField(to='provider.ProviderTransfer', on_delete=models.PROTECT, null=True,
                                             blank=True)
    handling = models.BooleanField(default=False)

    @property
    def asset(self):
        return self.wallet.asset

    def get_explorer_link(self) -> str:
        return self.network.explorer_link.format(hash=self.trx_hash)

    def build_trx(self):
        if self.deposit and self.is_fee:
            logger.info(f'Creating Trx for transfer id: {self.id} ignored.')
            return None

        asset = self.wallet.asset
        out_wallet = asset.get_wallet(Account.out())

        if self.deposit:
            sender, receiver = out_wallet, self.wallet
        else:
            sender, receiver = self.wallet, out_wallet

        Trx.transaction(
            group_id=self.group_id,
            sender=sender,
            receiver=receiver,
            amount=self.amount,
            scope=Trx.TRANSFER
        )

        if self.fee_amount:
            Trx.transaction(
                group_id=self.group_id,
                sender=sender,
                receiver=asset.get_wallet(Account.system()),
                amount=self.fee_amount,
                scope=Trx.COMMISSION
            )

    @classmethod
    def new_withdraw(cls, wallet: Wallet, network: Network, amount: Decimal, address: str):
        assert wallet.asset.symbol != Asset.IRT

        network_asset = NetworkAsset.objects.get(network=network, asset=wallet.asset)
        assert network_asset.withdraw_max >= amount >= max(network_asset.withdraw_min, network_asset.withdraw_fee)

        lock = wallet.lock_balance(amount)
        deposit_address = network.get_deposit_address(wallet.account)

        commission = network_asset.withdraw_fee

        transfer = Transfer.objects.create(
            wallet=wallet,
            network=network,
            amount=amount - commission,
            fee_amount=commission,
            lock=lock,
            source=cls.BINANCE,
            deposit_address=deposit_address,
            out_address=address,
            deposit=False
        )

        from ledger.tasks import create_binance_withdraw
        create_binance_withdraw.delay(transfer.id)

        return transfer

    def save(self, *args, **kwargs):
        if self.status == self.DONE:
            self.update_crypto_balances()

        return super().save(*args, **kwargs)

    def update_crypto_balances(self):
        try:
            balance, _ = CryptoBalance.objects.get_or_create(
                deposit_address=self.deposit_address,
                asset=self.wallet.asset,
            )
            balance.update()
            if DEFAULT_COIN_OF_NETWORK.get(self.network.symbol) != self.wallet.asset.symbol:
                balance, _ = CryptoBalance.objects.get_or_create(
                    deposit_address=self.deposit_address,
                    asset=Asset.objects.get(symbol=DEFAULT_COIN_OF_NETWORK.get(self.network.symbol)),
                )
                balance.update()

            if deposit_address := DepositAddress.objects.filter(address=self.out_address).first():
                balance, _ = CryptoBalance.objects.get_or_create(
                    deposit_address=deposit_address,
                    asset=self.wallet.asset,
                )
                balance.update()

        except Exception:
            logger.exception('failed to update crypto balance')

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["trx_hash", "network"],
                name="unique_transfer_tx_hash_network",
                condition=Q(status__in=["pending", "confirmed"]),
            )
        ]
