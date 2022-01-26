import logging
from abc import ABC, abstractmethod

from ledger.models import Transfer
from tracker.models import BlockTracker

logger = logging.getLogger(__name__)


class Reverter(ABC):
    @abstractmethod
    def from_number(self, number):
        pass


class ETHReverter(Reverter):
    def from_number(self, number):
        logger.info('Reverting to block number: {}'.format(number))

        blocks = BlockTracker.objects.filter(number__gte=number)
        for block in blocks:
            Transfer.objects.filter(block_hash=block.hash, deposit=True).update(status=Transfer.REVERTED)
        blocks.delete()
