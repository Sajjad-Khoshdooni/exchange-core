from _helpers.blockchain.bsc import get_web3_bsc_client
from _helpers.blockchain.tron import get_tron_client
from ledger.models import Network
from tracker.blockchain.bsc.history_builder import BSCRequester
from tracker.blockchain.requester import Requester
from tracker.blockchain.trx.history_builder import TRXRequester


class RequesterFactory:
    @staticmethod
    def build(network: Network) -> 'Requester':
        if network.symbol == 'TRX':
            return TRXRequester(get_tron_client())
        if network.symbol == 'BSC':
            return BSCRequester(get_web3_bsc_client())
        raise NotImplementedError
