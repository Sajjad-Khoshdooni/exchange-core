from typing import List

from web3 import Web3
from web3.types import BlockData

from _helpers.blockchain.bsc import get_web3_bsc_client, bsc
from ledger.models import Asset
from tracker.blockchain.dtos import BlockDTO, RawTransactionDTO, TransactionDTO
from tracker.blockchain.requester import Requester
from tracker.blockchain.transfer_creator import TransactionParser, CoinHandler

TRANSFER_METHOD_ID = 'a9059cbb'
TRANSFER_FROM_METHOD_ID = '23b872dd'

BEP20_SYMBOL_TO_SMART_CONTRACT = {
    'ETH': '0x2170ed0880ac9a755fd29b2688956bd959f933f8', 'USDT': '0x55d398326f99059ff775485246999027b3197955',
    'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c', 'USDC': '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d',
    'XRP': '0x1d2f0da169ceb9fc7b3144628db156f3f6c60dbe', 'ADA': '0x3ee2200efb3400fabb9aacf31297cbdd1d435d47',
    'AVAX': '0x1ce0c2827e2ef14d5c4f29a091d735a204794041', 'DOT': '0x7083609fce4d1d8dc0c979aab8c869ea2c873402',
    'DOGE': '0xba2ae424d960c26247dd6c32edc70b295c744c43', 'SHIB': '0x2859e4544c4bb03966803b044a93563bd2d0dd4d',
    'BUSD': '0xe9e7cea3dedca5984780bafc599bd69add087d56', 'UST': '0x23396cf899ca06c4472205fc903bdb4de249d6fc',
    'DAI': '0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3', 'LTC': '0x4338665cbb7b2485a8855a139b75d5e34ab0db94',
    'ATOM': '0x0eb3a705fc54725037cc9e008bdede697f62f335', 'LINK': '0xf8a0bf9cf54bb92f17374d9e9a321e6a111a51bd',
    'NEAR': '0x1fa4a73a3f0133f0025378af00236f3abdee5d63', 'UNI': '0xbf5140a22578168fd562dccf235e5d43a02ce9b1',
    'TRX': '0x85eac5ac2f758618dfa09bdbe0cf174e7d574d5b', 'BCH': '0x8ff795a6f4d97e7887c79bea79aba5cc76444adf',
    'FTM': '0xad29abb318791d579433d831ed122afeaf29dcfe', 'AXS': '0x715d400f88c167884bbcc41c5fea407ed4d2f8a0',
    'BTCB': '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c', 'ETC': '0x3d6545b08693dae087e957cb1180ee38b9e3c25e',
    'XTZ': '0x16939ef78684453bfdfb47825f8a5f714f12623a', 'EGLD': '0xbf7c81fff98bbe61b40ed186e4afd6ddd01337fe',
    'IOTA': '0xd944f1d1e9d5f9bb90b62f9d45e447d989580782', 'GALA': '0x7ddee176f665cd201f93eede625770e2fd911990',
    'FRAX': '0x90c97f71e18723b0cf0dfa30ee176ab653e89f40', 'EOS': '0x56b6fb708fc5732dec1afc8d8556423a2edccbd6',
    'FLOW': '0xc943c5320b9c18c153d1e2d12cc3074bebfb31a2', 'BTT': '0x352Cb5E19b12FC216548a2677bD0fce83BaE434B',
    'MKR': '0x5f0da599bb2cccfcf6fdfd7d81743b6020864350', 'XEC': '0x0ef2e7602add1733bfdb17ac3094d0421b502ca3',
    'ZEC': '0x1ba42e5193dfa8b03d15dd1b86a3113bbbef8eeb', 'TUSD': '0x14016e85a25aeb13065688cafb43044c2ef86784',
    'BAT': '0x101d82428437127bf1608f699cd651e6abf9766e', 'USDP': '0xb3c11196a4f3b1da7c23d9fb0a3dde9c6340934f',
    'IOTX': '0x9678e42cebeb63f23197d726b29b1cb20d0064e5', 'SFM': '0x42981d0bfbAf196529376EE702F2a9Eb9092fcB5',
    'COMP': '0x52ce071bd9b1c4b00a0b92d298c512478cad67e8', 'PAX': '0xb7f8cd00c5a06c0537e2abff0b58033d02e5e094',
    'YFI': '0x88f1a5ae2a3bf98aeaf342d26b30a79438c9142e', '1INCH': '0x111111111117dc0aa78b770fa6a738034120c302',
    'SLP': '0x070a08beef8d36734dd67a491202ff35a6a16d97', 'ZIL': '0xb86abcb37c3a4b64f74f59301aff131a1becc787',
    'FXS': '0xe48a3d7d0bc88d552f730b62c006bc925eadb9ee', 'ANKR': '0xf307910a4c7bbc79691fd374889b36d8531b08e3',
    'BNT': '0xa069008a669e2af00a86673d9d584cfb524a42cc', 'NFT': '0x1fc9004ec7e5722891f5f38bae7678efcb11d34d',
    'BabyDoge': '0xc748673057861a797275CD8A068AbB95A902e8de', 'SNX': '0x9ac983826058b8a9c7aa1c9171441191232e8404',
    'ONT': '0xfd7b3a77848f1c2d67e05e54d78d174a0c850335', 'ANY': '0xf68c9df95a18b2a5a5fa1124d79eeeffbad0b6fa',
    'WRX': '0x8e17ed70334c87ece574c9d537bc153d8609e2a3', 'JST': '0xea998d307aca04d4f0a3b3036aba84ae2e409c0a',
    'PAXG': '0x7950865a9140cb519342433146ed5b40c6f210f7', 'C98': '0xaec945e04baf28b135fa7c640f624f8d90f1c3a6',
    'TLOS': '0xb6c53431608e626ac81a9776ac3e999c5556717c', 'CELR': '0x1f9f6a696c6fd109cd3956f45dc709d2b3902163',
    'SXP': '0x47bead2563dcbf3bf2c9407fea4dc236faba485a', 'CTSI': '0x8da443f84fea710266c8eb6bc34b71702d033ef2',
    'COTI': '0xadbaf88b39d37dc68775ed1541f1bf83a5a45feb', 'REEF': '0xf21768ccbc73ea5b6fd3c687208a7c2def2d966e',
    'TWT': '0x4b0f1812e5df2a09796481ff14017e6005508003', 'ELF': '0xa3f020a5c92e15be13caf0ee5c95cf79585eecc9',
    'KNC': '0xfe56d5892bdffc7bf58f2e84be1b2c32d21c308b', 'ALPHA': '0xa1faa113cbe53436df28ff0aee54275c13b40975',
    'bCFX': '0x045c4324039dA91c52C55DF5D785385Aab073DcF', 'vBTC': '0x882c173bc7ff3b7786ca16dfed3dfffb9ee7847b',
    'SUN': '0xa1e6c58d503e4eee986167f45a063853cefe08c3', 'PROM': '0xaf53d56ff99f1322515e54fdde93ff8b3b7dafd5',
    'BIFI': '0xCa3F508B8e4Dd382eE878A314789373D80A5190A', 'TLM': '0x2222227e22102fe3322098e4cbfe18cfebd57c95',
    'FEG': '0xacfc95585d80ab62f67a14c566c1b7a49fe91167', 'POLS': '0x7e624fa0e1c4abfd309cc15719b7e2580887f570',
    'DODO': '0x67ee3cb086f8a16f34bee3ca72fad36f7db929e2', 'ALICE': '0xac51066d7bec65dc4589368da368b212745d63e8',
    '$DG': '0x9fdc3ae5c814b79dca2556564047c5e7e5449c19', 'BAKE': '0xE02dF9e3e622DeBdD69fb838bB799E3F168902c5',
    'BAND': '0xad6caeb32cd2c308980a548bd0bc5aa4306c6c18', 'KOGE': '0xe6df05ce8c8301223373cf5b969afcb1498c5528',
    'vETH': '0xf508fcd89b8bd15579dc79a6827cb4686a3592c8', 'BTCST': '0x78650b139471520656b9e7aa7a5e9276814a38e9',
    'XVS': '0xcf6bb5389c92bdda8a3747ddb454cb7a64626c63', 'BZRX': '0x4b87642aedf10b642be4663db842ecc5a88bf5ba',
    'RFOX': '0x0a3a21356793b49154fd3bbe91cbc2a16c0457f5', 'EPS': '0xa7f552078dcc247c2684336020c03648500c6d9f',
    'FUSE': '0x5857c96dae9cf8511b08cb07f85753c472d36ea3', 'MIR': '0x5b6dcf557e2abe2323c48445e8cc948910d8c2c9',
    'vUSDC': '0xeca88125a5adbe82614ffc12d0db554e2e2867c8', 'RISE': '0x0cD022ddE27169b20895e0e2B2B8A33B25e63579',
    'SFP': '0xd41fdb03ba84762dd66a0af1a6c8540ff1ba5dfb', 'CTK': '0xa8c2b8eec3d368c0253ad3dae65a5f2bbb89c929',
    'ATA': '0xa2120b9e674d3fc3875f415a7df52e382f141225', 'YFII': '0x7f70642d88cf1c4a3a7abb072b53b929b653eda5',
    'SAITO': '0x3c6dad0475d3a1696b359dc04c99fd401be134da', 'QANX': '0xaaa7a10a8ee237ea61e8ac46c50a8db8bcc1baaa',
    'LTO': '0x857b222fc79e1cbbf8ca5f78cb133d1b7cf34bbd', 'SUSHI': '0x947950bcc74888a40ffa2593c5798f11fc9124c4',
    'BTC': '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c', 'FIL': '0x0d8ce2a99bb6e3b7db580ed848240e4a0f9ae153',
    'MATIC': '0xcc42724c6683b7e57334c4e856f4c9965ed682bd', 'SOL': '0xfea6ab80cd850c3e63374bc737479aeec0e8b9a1',
    'AAVE': '0xfb6115445bff7b52feb98650c87f44907e58f802'
}


# TODO: check XLM


class BSCCoinBSCHandler(CoinHandler):
    def __init__(self):
        self.asset = Asset.objects.get(symbol='BNB')

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            t['input'] == '0x' and
            t['to'] is not None
        )

    def build_transaction_data(self, t):
        t = t.raw_transaction
        return TransactionDTO(
            to_address=t['to'].lower(),
            amount=t['value'] / 10 ** 18,
            from_address=t['from'].lower(),
            id=t['hash'].hex(),
            asset=self.asset
        )


class BEP20CoinBSCHandler(CoinHandler):

    def __init__(self):
        self.web3 = get_web3_bsc_client()
        self.smart_contract_to_symbol = {v: k for k, v in BEP20_SYMBOL_TO_SMART_CONTRACT.items()}
        self.all_asset_symbols = Asset.objects.all().values_list('symbol', flat=True)

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            t['to'] and
            t['to'].lower() in BEP20_SYMBOL_TO_SMART_CONTRACT.values() and
            t['input'][2:10] in [TRANSFER_METHOD_ID, TRANSFER_FROM_METHOD_ID] and
            self.smart_contract_to_symbol.get(t['to'].lower()) in self.all_asset_symbols
        )

    def get_asset(self, t):
        if symbol := self.smart_contract_to_symbol.get(t['to'].lower()):
            return Asset.objects.get(symbol=symbol)
        raise NotImplementedError

    def build_transaction_data(self, t):
        t = t.raw_transaction

        contract = self.web3.eth.contract(self.web3.toChecksumAddress(t['to'].lower()),
                                          abi=bsc.get_bsc_abi(t['to'].lower()))
        function, decoded_input = contract.decode_function_input(t['input'])
        if function.function_identifier == 'transfer':
            return TransactionDTO(
                to_address=decoded_input['recipient'].lower(),
                amount=decoded_input['amount'] / 10 ** 18,
                from_address=t['from'].lower(),
                id=t['hash'].hex(),
                asset=self.get_asset(t)
            )
        if function.function_identifier == 'transferFrom':
            return TransactionDTO(
                to_address=decoded_input['recipient'].lower(),
                amount=decoded_input['amount'] / 10 ** 18,
                from_address=decoded_input['sender'].lower(),
                id=t['hash'].hex(),
                asset=self.get_asset(t)
            )


class BSCTransactionParser(TransactionParser):

    def list_of_raw_transaction_from_block(self, block: BlockDTO) -> List[RawTransactionDTO]:
        return [RawTransactionDTO(
            id=t['hash'].hex().lower(),
            raw_transaction=t
        ) for t in block.raw_block.get('transactions', [])]


class BSCRequester(Requester):
    def __init__(self, bsc_web3: Web3):
        self.web3 = bsc_web3

    @staticmethod
    def build_block_dto_from_dict(data: BlockData) -> BlockDTO:
        return BlockDTO(
            id=data['hash'].hex().lower(),
            number=data['number'],
            parent_id=data['parentHash'].hex().lower(),
            timestamp=data['timestamp'] * 1000,
            raw_block=data
        )

    def get_latest_block(self):
        return self.build_block_dto_from_dict(
            self.web3.eth.get_block('latest', full_transactions=True)
        )

    def get_block_by_id(self, _hash):
        return self.build_block_dto_from_dict(self.web3.eth.get_block(_hash, full_transactions=True))

    def get_block_by_number(self, number):
        return self.build_block_dto_from_dict(self.web3.eth.get_block(number, full_transactions=True))
