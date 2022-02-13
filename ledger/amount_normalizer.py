from decimal import Decimal
from typing import NewType

NormalizedAmount = NewType('NormalizedAmount', Decimal)


class AmountNormalizer:
    NETWORK_ASSET_DECIMAL_POINT = {
        'TRX': {
            'TRX': 6,
            'USDT': 6,
        },
        'BSC': {
            'BNB': 18,
            'USDT': 18,
        },
        'ETH': {
            'ETH': 18,
            'USDT': 18,
        }
    }

    def __init__(self, network, asset):
        self.network = network
        self.asset = asset
        self.decimal_point_number = self.NETWORK_ASSET_DECIMAL_POINT.get(self.network.symbol, {}).get(self.asset.symbol)
        if self.decimal_point_number is None:
            raise NotImplementedError

    def from_decimal_to_int(self, amount: NormalizedAmount) -> int:
        return int(amount * (10 ** self.decimal_point_number))

    def from_int_to_decimal(self, amount: int) -> NormalizedAmount:
        return Decimal(amount) / (10 ** self.decimal_point_number)
