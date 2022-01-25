from django.db import models


class BlockTracker(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    number = models.PositiveIntegerField(db_index=True, unique=True)
    hash = models.CharField(max_length=128, unique=True, db_index=True)
    block_date = models.DateTimeField()

    @classmethod
    def get_latest_block(cls) -> 'BlockTracker':
        return BlockTracker.objects.order_by('number').last()

    @classmethod
    def has(cls, block_hash: str):
        return BlockTracker.objects.filter(hash=block_hash).exists()