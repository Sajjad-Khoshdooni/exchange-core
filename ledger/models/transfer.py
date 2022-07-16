import logging
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models, transaction
from django.db.models import CheckConstraint
from django.db.models import UniqueConstraint, Q
from yekta_config.config import config

from accounts.models import Account, Notification
from accounts.utils import email
from accounts.utils.push_notif import send_push_notif
from ledger.consts import DEFAULT_COIN_OF_NETWORK
from ledger.models import Trx, NetworkAsset, Asset, DepositAddress
from ledger.models import Wallet, Network
from ledger.models.address_key import AddressKey
from ledger.models.crypto_balance import CryptoBalance
from ledger.utils.fields import get_amount_field, get_address_field
from ledger.utils.precision import humanize_number
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class Transfer(models.Model):
    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done'
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

    trx_hash = models.CharField(max_length=128, db_index=True, null=True, blank=True)
    block_hash = models.CharField(max_length=128, db_index=True, blank=True)
    block_number = models.PositiveIntegerField(null=True, blank=True)

    out_address = get_address_field()
    memo = models.CharField(max_length=64, blank=True)

    is_fee = models.BooleanField(default=False)

    source = models.CharField(max_length=8, default=SELF, choices=((SELF, SELF), (BINANCE, BINANCE)))
    provider_transfer = models.OneToOneField(to='provider.ProviderTransfer', on_delete=models.PROTECT, null=True,
                                             blank=True)
    handling = models.BooleanField(default=False)

    hidden = models.BooleanField(default=False)

    @property
    def asset(self):
        return self.wallet.asset

    @property
    def total_amount(self):
        return self.amount + self.fee_amount

    def get_explorer_link(self) -> str:
        if not self.trx_hash:
            return ''

        if 'Internal transfer' in self.trx_hash:
            return ''

        return self.network.explorer_link.format(hash=self.trx_hash)

    def build_trx(self, pipeline: WalletPipeline):
        if self.hidden or (self.deposit and self.is_fee):
            logger.info(f'Creating Trx for transfer id: {self.id} ignored.')
            return

        asset = self.wallet.asset
        out_wallet = asset.get_wallet(Account.out())

        if self.deposit:
            sender, receiver = out_wallet, self.wallet
        else:
            sender, receiver = self.wallet, out_wallet

        pipeline.new_trx(
            group_id=self.group_id,
            sender=sender,
            receiver=receiver,
            amount=self.amount,
            scope=Trx.TRANSFER
        )

        if self.fee_amount:
            pipeline.new_trx(
                group_id=self.group_id,
                sender=sender,
                receiver=asset.get_wallet(Account.system()),
                amount=self.fee_amount,
                scope=Trx.COMMISSION
            )

    @classmethod
    def check_fast_forward(cls, sender_wallet: Wallet, network: Network, amount: Decimal, address: str):
        if not DepositAddress.objects.filter(address=address).exists():
            return False
        sender_deposit_address = DepositAddress.get_deposit_address(
            account=sender_wallet.account,
            network=network
        )

        receiver_account = DepositAddress.objects.filter(address=address).first().address_key.account
        receiver_deposit_address = DepositAddress.get_deposit_address(
            account=receiver_account,
            network=network
        )
        receiver_wallet = sender_wallet.asset.get_wallet(receiver_account)

        group_id = uuid4()

        with WalletPipeline() as pipeline:
            pipeline.new_trx(
                sender=sender_wallet,
                receiver=receiver_wallet,
                scope=Trx.TRANSFER,
                group_id=group_id,
                amount=amount
            )
            Transfer.objects.create(
                status=Transfer.DONE,
                deposit_address=sender_deposit_address,
                wallet=sender_wallet,
                network=network,
                amount=amount,
                deposit=False,
                group_id=group_id,
                trx_hash='internal: <%s>' % str(group_id),
                out_address=address
            )
            Transfer.objects.create(
                status=Transfer.DONE,
                deposit_address=receiver_deposit_address,
                wallet=receiver_wallet,
                network=network,
                amount=amount,
                deposit=True,
                group_id=group_id,
                trx_hash='internal: <%s>' % str(group_id),
                out_address=sender_deposit_address.address
            )
            return True

    @classmethod
    def new_withdraw(cls, wallet: Wallet, network: Network, amount: Decimal, address: str, memo: str = ''):
        assert wallet.asset.symbol != Asset.IRT
        assert wallet.account.is_ordinary_user()
        wallet.has_balance(amount, raise_exception=True)

        if cls.check_fast_forward(sender_wallet=wallet, network=network, amount=amount, address=address):
            return

        network_asset = NetworkAsset.objects.get(network=network, asset=wallet.asset)
        assert network_asset.withdraw_max >= amount >= max(network_asset.withdraw_min, network_asset.withdraw_fee)

        commission = network_asset.withdraw_fee

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            transfer = Transfer.objects.create(
                wallet=wallet,
                network=network,
                amount=amount,
                fee_amount=commission,
                source=cls.source,
                out_address=address,
                deposit=False,
                memo=memo,
            )

            pipeline.new_lock(key=transfer.group_id, wallet=wallet, amount=amount, reason=WalletPipeline.WITHDRAW)

        from ledger.tasks import create_withdraw
        create_withdraw.delay(transfer.id)

        return transfer

    def save(self, *args, **kwargs):
        if self.source == self.SELF and self.status == self.DONE and not settings.DEBUG:
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

    def alert_user(self):
        user = self.wallet.account.user

        if self.status == Transfer.DONE and not self.hidden and user and user.is_active:
            sent_amount = self.asset.get_presentation_amount(self.amount)
            user_email = self.wallet.account.user.email
            if self.deposit:
                title = 'دریافت شد: %s %s' % (humanize_number(sent_amount), self.wallet.asset.symbol)
                message = 'از ادرس %s...%s ' % (self.out_address[-8:], self.out_address[:9])
                template = email.SCOPE_DEPOSIT_EMAIL

            else:
                title = 'ارسال شد: %s %s' % (humanize_number(sent_amount), self.wallet.asset.symbol)
                message = 'به ادرس %s...%s ' % (self.out_address[-8:], self.out_address[:9])
                template = email.SCOPE_WITHDRAW_EMAIL

            Notification.send(
                recipient=self.wallet.account.user,
                title=title,
                message=message
            )

            send_push_notif(user=user, title=title, message=message)

            if user_email:
                email.send_email_by_template(
                    recipient=user_email,
                    template=template,
                    context={
                        'amount': humanize_number(sent_amount),
                        'wallet_asset': self.wallet.asset.symbol,
                        'withdraw_address': self.out_address,
                        'trx_hash': self.trx_hash,
                        'brand': config('BRAND'),
                        'panel_url': config('PANEL_URL'),
                        'logo_elastic_url': config('LOGO_ELASTIC_URL'),
                    }
                )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["trx_hash", "network", "deposit"],
                name="unique_transfer_tx_hash_network",
                condition=Q(status__in=["pending", "done"]),
            ),
            CheckConstraint(check=Q(amount__gte=0, fee_amount__gte=0), name='check_ledger_transfer_amounts', ),
        ]
