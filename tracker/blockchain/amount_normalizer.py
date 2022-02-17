from decimal import Decimal

from ledger.models import Asset, Network

NETWORK_ASSET_DECIMAL_POINT = {
    'TRX': {
        'DEFAULT': 6,
    },
    'BSC': {
        'DEFAULT': 18,
        'DOGE': 8,
        'ZIL': 12,
        'ALICE': 6,
    },
    'ETH': {
        'DEFAULT': 18,
    }
}


class AmountNormalizer:

    def __init__(self, network: Network):
        self._network_map = NETWORK_ASSET_DECIMAL_POINT[network.symbol]

    def get_amount_power(self, asset: Asset) -> int:
        return self._network_map.get(asset.symbol, self._network_map.get('DEFAULT'))

    def from_decimal_to_int(self, asset: Asset, amount: Decimal) -> int:
        return int(amount * (10 ** self.get_amount_power(asset)))

    def from_int_to_decimal(self, asset: Asset, amount: int) -> Decimal:
        return Decimal(amount) / (10 ** self.get_amount_power(asset))
