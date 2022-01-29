import logging

from ledger.models import Transfer

logger = logging.getLogger(__name__)


class Reverter:
    def __init__(self, block_tracker):
        self.block_tracker = block_tracker

    def from_number(self, number):
        logger.info('Reverting to block number: {}'.format(number))

        blocks = self.block_tracker.objects.filter(number__gte=number)
        for block in blocks:
            Transfer.objects.filter(block_hash=block.hash).update(status=Transfer.REVERTED)
        blocks.delete()
