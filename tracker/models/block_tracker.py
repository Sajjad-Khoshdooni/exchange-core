from django.db import models

from ledger.models import Network


class BlockTracker(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    number = models.PositiveIntegerField(db_index=True)
    hash = models.CharField(max_length=128, unique=True, db_index=True)
    block_date = models.DateTimeField()
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)

    @classmethod
    def get_latest_block(cls) -> 'BlockTracker':
        return cls.objects.order_by('number').last()

    @classmethod
    def has(cls, block_hash: str):
        return cls.objects.filter(hash=block_hash).exists()

    class Meta:
        unique_together = ('number', 'network')


class ETHBlockTrackerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(network__symbol=Network.ETH)


class ETHBlockTracker(BlockTracker):
    objects = ETHBlockTrackerManager()

    def save(self, *args, **kwargs):
        self.network = Network.objects.get(symbol=Network.ETH)
        super().save(*args, **kwargs)

    class Meta:
        proxy = True


class TRXBlockTrackerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(network__symbol=Network.TRX)


class TRXBlockTracker(BlockTracker):
    objects = TRXBlockTrackerManager()

    def save(self, *args, **kwargs):
        self.network = Network.objects.get(symbol=Network.TRX)
        super().save(*args, **kwargs)

    class Meta:
        proxy = True


class BSCBlockTrackerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(network__symbol=Network.BSC)


class BSCBlockTracker(BlockTracker):
    objects = BSCBlockTrackerManager()

    def save(self, *args, **kwargs):
        self.network = Network.objects.get(symbol=Network.BSC)
        super().save(*args, **kwargs)

    class Meta:
        proxy = True
