from decimal import Decimal
from uuid import UUID

from ledger.models import Wallet, BalanceLock


class WalletUpdater:
    def __init__(self):
        self._decrease_locks = []

    def release_lock(self, balance_lock: BalanceLock, amount: Decimal = 0, full: bool = False):
        self._decrease_locks.append()

    def new_trx(self, sender: Wallet, receiver: Wallet, amount: Decimal, scope: str, group_id: UUID):
        pass

