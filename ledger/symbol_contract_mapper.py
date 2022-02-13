from typing import Dict

from ledger.consts import BEP20_SYMBOL_TO_SMART_CONTRACT, ERC20_SYMBOL_TO_SMART_CONTRACT


class SymbolContractMapper:
    def __init__(self, symbol_to_contract_map: Dict[str, str]):
        self.symbol_to_contract_map = symbol_to_contract_map
        self.contract_to_symbol_map = {v: k for k, v in symbol_to_contract_map.items()}

    def get_symbol_of_contract(self, contract):
        return self.contract_to_symbol_map.get(contract)

    def get_contract_of_symbol(self, symbol):
        return self.symbol_to_contract_map.get(symbol)

    def list_of_symbols(self):
        return self.symbol_to_contract_map.keys()

    def list_of_contracts(self):
        return self.contract_to_symbol_map.keys()


bep20_symbol_contract_mapper = SymbolContractMapper(BEP20_SYMBOL_TO_SMART_CONTRACT)
erc20_symbol_contract_mapper = SymbolContractMapper(ERC20_SYMBOL_TO_SMART_CONTRACT)
