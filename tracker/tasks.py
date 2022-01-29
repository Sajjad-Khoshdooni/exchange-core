from celery import shared_task

from tracker.blockchain.reverter import Reverter
from tracker.blockchain.trx.history_builder import TRXHistoryBuilder, TRXRequester, TRXTransferCreator
from tracker.models.block_tracker import TRXBlockTracker


@shared_task()
def trx_network_consumer(initial=False):
    TRXHistoryBuilder(
        TRXRequester(),
        Reverter(block_tracker=TRXBlockTracker),
        TRXTransferCreator()
    ).build(only_add_now_block=initial)
