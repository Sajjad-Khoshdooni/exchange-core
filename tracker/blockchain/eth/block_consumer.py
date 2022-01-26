import json
import logging
import signal
import sys
from datetime import datetime

import requests
import websocket
from django.db import transaction

from accounts.models import Account
from ledger.models import DepositAddress, Network, Trx, Asset, AddressSchema
from ledger.models.transfer import Transfer
from tracker.blockchain.eth.reverter import ETHReverter
from tracker.models import BlockTracker

logger = logging.getLogger(__name__)

INFURA_HTTPS_URL = 'https://rinkeby.infura.io/v3/3befd24cf53a4f889d632c3293c36d3e'
INFURA_WSS_URL = 'wss://rinkeby.infura.io/ws/v3/3befd24cf53a4f889d632c3293c36d3e'


class EthBlockConsumer:
    def __init__(self):
        self.loop = True
        self.subscription_id = None
        self.socket = websocket.WebSocket()

        logger.info('Starting ETH Node')

    def consume(self, initial: bool = False):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGQUIT, self.exit_gracefully)

        self.socket.connect(INFURA_WSS_URL)

        self.socket.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}))
        subscription = json.loads(self.socket.recv())
        logger.info('infura subscription: %s' % subscription)
        self.subscription_id = subscription['result']

        start = datetime.now()

        history_checked = initial  # ignore history on initial run

        while self.loop:
            block_str = self.socket.recv()
            logger.info('Now %s' % datetime.now())

            logger.info('Eth new block received: %s' % block_str)
            block_raw = json.loads(block_str)
            block = block_raw['params']['result']

            if not history_checked:
                logger.info('checking history')
                history_checked = True
                self.handle_history_gap(block)

            self.handle_new_block(block)

    def handle_history_gap(self, block: dict):
        parent_hash = block['parentHash']
        if BlockTracker.has(parent_hash):
            return

        to_handle_blocks = []

        for i in range(1000):
            if not self.loop:
                return

            logger.info('History query %s' % i)
            block = self.get_block_by_hash(parent_hash)
            to_handle_blocks.append(block)
            parent_hash = block['parentHash']

            if BlockTracker.has(parent_hash):
                break

        ETHReverter().from_number(int(block['number'], 16))
        for block in reversed(to_handle_blocks):
            self.handle_new_block(block)

    def get_block_by_hash(self, block_hash: str, trx_info: bool = True):
        response = requests.post(
            url=INFURA_HTTPS_URL,
            timeout=60,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByHash",
                "params": [block_hash, trx_info],
                "id": 1
            }
        )

        return response.json()['result']

    def exit_gracefully(self, signum, frame):
        self.loop = False

        if self.subscription_id:
            logger.info('Unsubscribing...')
            self.socket.send(
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_unsubscribe", "params": [self.subscription_id]}))

        logger.info('Closing socket...')

        self.socket.abort()
        self.socket.close()

        logger.info(f'{self.__class__.__name__} exited gracefully.')

        sys.exit()

    def handle_new_block(self, block: dict):
        block_hash = block['hash']

        if BlockTracker.has(block_hash):
            logger.warning('ignored duplicate block %s' % block_hash)
            return

        block_number = int(block['number'], 16)
        block_date = datetime.fromtimestamp(int(block['timestamp'], 16)).astimezone()

        last_db_block = BlockTracker.get_latest_block()
        if last_db_block:
            last_db_block_number = last_db_block.number
            number_diff = block_number - last_db_block_number
        else:
            # handle empty db block_tracker to continue normal condition
            number_diff = 1

        if number_diff < 1:
            ETHReverter().from_number(int(block['number'], 16))
            # chain reorg condition
            logger.info('reorg handling')
            pass

        elif number_diff > 1:
            # impossible condition
            raise Exception('number_diff > 1 received for block %s' % block_hash)

        self.handle_transactions(block)

        logger.info('Inserting block %d, %s' % (block_number, block_hash))
        BlockTracker.objects.create(number=block_number, hash=block_hash, block_date=block_date)

        self.handle_confirms(block)

    def handle_transactions(self, block: dict):
        block_hash = block['hash']
        block_number = int(block['number'], 16)
        asset = Asset.objects.get(symbol='ETH')

        if 'transactions' not in block:
            logger.info('re fetch block to access transactions %s' % block_number)
            block = self.get_block_by_hash(block_hash)

        raw_transactions = block['transactions']

        logger.info('Transactions %s' % len(raw_transactions))
        transactions = list(filter(lambda t: int(t['value'], 16) > 0, raw_transactions))
        logger.info('transactions reduced from %s to %s' % (len(raw_transactions), len(list(transactions))))

        to_address_to_trx = {t['to']: t for t in transactions}
        # trx_hashes = {t['hash']: t for t in transactions}

        with transaction.atomic():
            to_deposit_addresses = DepositAddress.objects.filter(
                schema__symbol=AddressSchema.ETH,
                address__in=to_address_to_trx
            )

            for deposit_address in to_deposit_addresses:
                trx_data = to_address_to_trx[deposit_address.address]

                Transfer.objects.create(
                    deposit_address=deposit_address,
                    wallet=asset.get_wallet(deposit_address.account),
                    amount=int(trx_data['value'], 16),
                    deposit=True,
                    trx_hash=trx_data['hash'],
                    block_hash=block_hash,
                    block_number=block_number,
                    out_address=trx_data['from']
                )

            # withdraws = Transfer.objects.filter(deposit=False, trx_hash__in=trx_hashes.keys())
            # for withdraw in withdraws:
            #     trx_data = from_network_wallets[network_wallet.address]
            #
            #     Transfer.objects.create(
            #         network_wallet=network_wallet,
            #         amount=int(trx_data['value'], 16),
            #         deposit=True,
            #         trx_hash=trx_data['hash'],
            #         block_hash=block_hash,
            #         block_number=block_number,
            #         out_address=trx_data['from']
            #     )

    def handle_confirms(self, block: dict):
        network_symbol = 'ETH'
        asset = Asset.objects.get(symbol=network_symbol)
        network = Network.objects.get(symbol=network_symbol)
        block_number = int(block['number'], 16)

        pending_transfers = Transfer.objects.filter(
            block_number__lte=block_number - network.minimum_block_to_confirm,
            status=Transfer.PENDING
        )

        for transfer in pending_transfers:
            if not BlockTracker.has(transfer.block_hash):
                transfer.status = Transfer.CANCELED
                transfer.save()
                continue

            with transaction.atomic():
                transfer.status = Transfer.DONE
                transfer.save()
                Trx.objects.create(
                    group_id=transfer.group_id,
                    sender=asset.get_wallet(Account.out()),
                    receiver=asset.get_wallet(transfer.deposit_address.account),
                    amount=transfer.amount,
                    scope=Trx.TRANSFER
                )
