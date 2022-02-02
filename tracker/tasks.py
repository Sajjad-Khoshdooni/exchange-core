from celery import shared_task

from _helpers.blockchain.tron import get_tron_client
from tracker.blockchain.block_info_populator import TRXBlockInfoPopulator
from tracker.blockchain.reverter import Reverter
from tracker.blockchain.trx.history_builder import TRXHistoryBuilder, TRXRequester, TRXTransferCreator
from tracker.models.block_tracker import TRXBlockTracker


@shared_task()
def trx_network_consumer(initial=False):
    TRXHistoryBuilder(
        TRXRequester(tron_client=get_tron_client()),
        Reverter(block_tracker=TRXBlockTracker),
        TRXTransferCreator()
    ).build(only_add_now_block=initial)


@shared_task()
def trx_add_block_info():
    TRXBlockInfoPopulator(tron_client=get_tron_client()).populate()
