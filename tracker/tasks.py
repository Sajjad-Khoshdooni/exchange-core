from celery import shared_task
from web3 import Web3

from _helpers.blockchain.bsc import get_web3_bsc_client
from _helpers.blockchain.tron import get_tron_client
from ledger.amount_normalizer import AmountNormalizer
from ledger.models import Network, Asset
from ledger.symbol_contract_mapper import bep20_symbol_contract_mapper, erc20_symbol_contract_mapper
from tracker.blockchain.abi_getter import BSCAbiGetter, ETHAbiGetter
from tracker.blockchain.block_info_populator import AllPopulatorGetter
from tracker.blockchain.confirmer import Confirmer
from tracker.blockchain.history_builder import HistoryBuilder
from tracker.blockchain.reverter import Reverter
from tracker.blockchain.transfer_creator import TransferCreator
from tracker.blockchain.trx.history_builder import (
    TRXRequester, TRXTransactionParser,
    USDTCoinTRXHandler, TRXCoinTRXHandler,
)
from tracker.blockchain.web3 import (
    Web3Requester, Web3BaseNetworkCoinHandler, Web3ERC20BasedCoinHandler,
    Web3TransactionParser,
)
from tracker.models.block_tracker import TRXBlockTracker, BSCBlockTracker, ETHBlockTracker


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
def bsc_network_consumer(initial=False):
    network = Network.objects.get(symbol='BSC')
    asset = Asset.objects.get(symbol='BNB')
    normalizer = AmountNormalizer(network=network, asset=asset)
    HistoryBuilder(
        requester=Web3Requester(get_web3_bsc_client()),
        reverter=Reverter(block_tracker=BSCBlockTracker),
        transfer_creator=TransferCreator(
            coin_handlers=[
                Web3BaseNetworkCoinHandler(base_network_asset=asset, amount_normalizer=normalizer),
                Web3ERC20BasedCoinHandler(
                    web3_client=get_web3_bsc_client(),
                    symbol_contract_mapper=bep20_symbol_contract_mapper,
                    amount_normalizer=normalizer,
                    abi_getter=BSCAbiGetter()
                )
            ],
            transaction_parser=Web3TransactionParser(),
            network=network
        ),
        network=network,
        block_tracker=BSCBlockTracker,
        confirmer=Confirmer(block_tracker=BSCBlockTracker, network=network),
    ).build(only_add_now_block=initial, maximum_block_step_for_backward=100)


@shared_task()
def eth_network_consumer(initial=False):
    network = Network.objects.get(symbol='ETH')
    asset = Network.objects.get(symbol='ETH')
    normalizer = AmountNormalizer(network=network, asset=asset)
    HistoryBuilder(
        requester=Web3Requester(Web3(Web3.HTTPProvider(
            'https://mainnet.infura.io/v3/3befd24cf53a4f889d632c3293c36d3e'))),
        reverter=Reverter(block_tracker=ETHBlockTracker),
        transfer_creator=TransferCreator(
            coin_handlers=[
                Web3BaseNetworkCoinHandler(base_network_asset=asset, amount_normalizer=normalizer),
                Web3ERC20BasedCoinHandler(
                    web3_client=Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/3befd24cf53a4f889d632c3293c36d3e')),
                    symbol_contract_mapper=erc20_symbol_contract_mapper,
                    amount_normalizer=normalizer,
                    abi_getter=ETHAbiGetter()
                )
            ],
            transaction_parser=Web3TransactionParser(),
            network=network
        ),
        network=network,
        block_tracker=ETHBlockTracker,
        confirmer=Confirmer(block_tracker=ETHBlockTracker, network=network),
    ).build(only_add_now_block=initial, maximum_block_step_for_backward=100)


@shared_task()
def add_block_infos():
    for populator in AllPopulatorGetter.get():
        populator.populate()
