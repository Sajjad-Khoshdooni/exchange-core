from dataclasses import dataclass
from typing import Any

from ledger.models import Asset


@dataclass
class RawTransactionDTO:
    id: str
    raw_transaction: Any


@dataclass
class TransactionDTO:
    id: str
    amount: int
    from_address: str
    to_address: str
    asset: Asset


@dataclass
class BlockDTO:
    id: str
    number: int
    parent_id: str
    timestamp: int  # with microseconds
    raw_block: Any
