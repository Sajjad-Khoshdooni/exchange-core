import uuid

from django.db import models

from accounts.models import Account

AMOUNT_MAX_DIGITS = 20
COMMISSION_MAX_DIGITS = 12
AMOUNT_DECIMAL_PLACES = 8


class Asset(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    coin = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)


class TransferNetworks(models.Model):
    network = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)


class AssetConfig(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)
    network = models.ForeignKey(TransferNetworks, on_delete=models.PROTECT)
    commission = models.DecimalField(max_length=COMMISSION_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    min_transfer = models.DecimalField(max_length=COMMISSION_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)

    class Meta:
        unique_together = ('asset', 'network')


class Wallet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    balance = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)


class WalletAddress(models.Model):
    asset_config = models.ForeignKey(AssetConfig, on_delete=models.PROTECT)

    address = models.CharField(max_length=256)
    address_tag = models.CharField(max_length=32, default='')


class Trx(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='received_trx')
    amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)

    group_id = models.UUIDField(default=uuid.uuid4, db_index=True)


class BalanceLock(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    release_date = models.DateTimeField()

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    freed = models.BooleanField(default=False, db_index=True)


class Order(models.Model):
    BUY, SELL = 'buy', 'sell'
    PENDING, CANCELLED, DONE = 'pend', 'cancel', 'done'

    created = models.DateTimeField(auto_now_add=True)

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    group_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    type = models.CharField(max_length=8, choices=[(BUY, BUY), (SELL, SELL)])
    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELLED, CANCELLED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField(BalanceLock, on_delete=models.CASCADE)


class Transfer(models.Model):
    PENDING, CANCELLED, DONE = 'pend', 'cancel', 'done'

    created = models.DateTimeField(auto_now_add=True)

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    group_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELLED, CANCELLED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField(BalanceLock, on_delete=models.CASCADE)

    out_address = models.CharField(max_length=256)
