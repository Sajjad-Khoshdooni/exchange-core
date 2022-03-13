from tracker.clients.bsc import get_web3_bsc_client
from tracker.clients.tron import get_tron_client
from ledger.models import Network
from tracker.blockchain.requester import Requester
from tracker.blockchain.trx.history_builder import TRXRequester
from tracker.blockchain.web3 import Web3Requester


class RequesterFactory:
    @staticmethod
    def build(network: Network) -> 'Requester':
        if network.symbol == 'TRX':
            return TRXRequester(get_tron_client())
        if network.symbol == 'BSC':
            return Web3Requester(get_web3_bsc_client())
        raise NotImplementedError
