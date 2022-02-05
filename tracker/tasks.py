from celery import shared_task

from _helpers.blockchain.tron import get_tron_client
from ledger.models import Network
from tracker.blockchain.block_info_populator import TRXBlockInfoPopulator
from tracker.blockchain.confirmer import Confirmer
from tracker.blockchain.history_builder import HistoryBuilder
from tracker.blockchain.reverter import Reverter
from tracker.blockchain.transfer_creator import TransferCreator
from tracker.blockchain.trx.history_builder import (
    TRXRequester, TRXTransactionParser,
    USDTCoinTRXHandler, TRXCoinTRXHandler,
)

from tracker.models.block_tracker import TRXBlockTracker


@shared_task()
def trx_network_consumer(initial=False):
    network = Network.objects.get(symbol='TRX')
    HistoryBuilder(
        requester=TRXRequester(get_tron_client()),
        reverter=Reverter(block_tracker=TRXBlockTracker),
        transfer_creator=TransferCreator(
            coin_handlers=[USDTCoinTRXHandler(), TRXCoinTRXHandler()],
            transaction_parser=TRXTransactionParser(),
            network=network
        ),
        network=network,
        block_tracker=TRXBlockTracker,
        confirmer=Confirmer(block_tracker=TRXBlockTracker, network=network),
    ).build(only_add_now_block=initial, maximum_block_step_for_backward=100)


@shared_task()
def trx_add_block_info():
    TRXBlockInfoPopulator(tron_client=get_tron_client()).populate()
