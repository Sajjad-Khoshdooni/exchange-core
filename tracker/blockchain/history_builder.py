import logging
from datetime import datetime
from typing import Type

from django.db import transaction

from ledger.models import Network
from tracker.blockchain.confirmer import Confirmer
from tracker.blockchain.dtos import BlockDTO
from tracker.blockchain.requester import Requester
from tracker.blockchain.reverter import Reverter
from tracker.blockchain.transfer_creator import TransferCreator
from tracker.models import BlockTracker

logger = logging.getLogger(__name__)


class HistoryBuilder:

    def __init__(self, requester: Requester, reverter: Reverter, transfer_creator: TransferCreator,
                 network: Network, block_tracker: Type[BlockTracker], confirmer: Confirmer):
        self.requester = requester
        self.reverter = reverter
        self.transfer_creator = transfer_creator
        self.network = network
        self.block_tracker = block_tracker
        self.confirmer = confirmer

    def build(self, only_add_now_block=False, maximum_block_step_for_backward=1000):
        block = self.requester.get_latest_block()
        if self.block_tracker.has(block.id):
            return

        if only_add_now_block:
            self.add_block(block)
        elif (
            block.number - self.block_tracker.get_latest_block().number
            >= maximum_block_step_for_backward
        ):
            self.forward_fulfill(block)
        else:
            self.backward_fulfill(block)

        self.confirmer.confirm(block)

    def forward_fulfill(self, block: BlockDTO):
        system_latest_block = self.block_tracker.atest_block()

        _from = system_latest_block.number + 1
        _to = block.number - self.network.min_confirm

        for i in range(_from, _to):
            block = self.requester.get_block_by_number(i)
            self.add_block(block)

    def backward_fulfill(self, block: BlockDTO):
        blocks = [block]

        while not self.block_tracker.has(blocks[-1].parent_id):
            blocks.append(self.requester.get_block_by_id(blocks[-1].parent_id))

        self.reverter.from_number(blocks[-1].number)
        for block in reversed(blocks):
            self.add_block(block)

    def add_block(self, block):
        self.transfer_creator.from_block(block)
        created_block = self.block_tracker.objects.create(
            number=block.number,
            hash=block.id,
            block_date=datetime.fromtimestamp(block.timestamp / 1000).astimezone(),
        )
        logger.info(f'(HistoryBuilder-{self.network}) Block number: {created_block.number}, hash: {created_block.hash} '
                    f'created.')
