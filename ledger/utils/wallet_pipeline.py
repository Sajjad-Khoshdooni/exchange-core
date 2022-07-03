from collections import defaultdict
from decimal import Decimal
from typing import Union
from uuid import UUID

from django.db.models import F
from django.db.transaction import Atomic

from ledger.utils.fields import AMOUNT_PRECISION


def sorted_flatten_dict(data: dict) -> list:
    if not data:
        return []

    return sorted(data.items(), key=lambda x: x[0])


class WalletPipeline(Atomic):
    TRADE, WITHDRAW = 'trade', 'withdraw'

    def __init__(self, verbose: bool = False):
        super(WalletPipeline, self).__init__(using=None, savepoint=True, durable=False)
        self.verbose = verbose

    def __enter__(self):
        super(WalletPipeline, self).__enter__()

        self._wallet_locks = defaultdict(Decimal)
        self._wallet_balances = defaultdict(Decimal)

        self._trxs = []

        self._locks = {}
        self._locks_amount = defaultdict(Decimal)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._execute()
        finally:
            super(WalletPipeline, self).__exit__(exc_type, exc_val, exc_tb)

    def new_lock(self, key: UUID, wallet, amount: Union[int, Decimal], reason: str):
        from ledger.models import BalanceLock
        from ledger.models import Wallet

        assert amount > 0

        if isinstance(key, str):
            key = UUID(key)

        assert isinstance(key, UUID)

        if not wallet.check_balance:
            return

        allowed_locking = [
            (Wallet.SPOT, self.TRADE), (Wallet.SPOT, self.WITHDRAW),
            (Wallet.MARGIN, self.TRADE)
        ]

        assert (wallet.market, reason) in allowed_locking

        wallet.locked += amount

        lock = BalanceLock(
            key=key,
            wallet=wallet,
            amount=amount,
            original_amount=amount,
            reason=reason
        )

        self._locks[key] = lock
        self._wallet_locks[wallet.id] += amount

    def release_lock(self, key: UUID, amount: Union[Decimal, int] = None):
        from ledger.models import BalanceLock

        assert amount is None or amount >= 0

        if isinstance(key, str):
            key = UUID(key)

        assert isinstance(key, UUID)

        # check first new locks
        if key in self._locks:
            lock = self._locks[key]

            if amount is None:
                amount = lock.amount

            lock.amount -= amount
            self._wallet_locks[lock.wallet_id] -= amount

            if lock.amount == 0:
                del self._locks[key]

        else:
            lock = BalanceLock.objects.filter(key=key).first()

            if not lock:
                return

            if amount is None:
                amount = lock.amount

            self._locks_amount[key] -= amount
            self._wallet_locks[lock.wallet_id] -= amount

    def new_trx(self, sender, receiver, amount: Union[Decimal, int], scope: str, group_id: UUID):
        from ledger.models.trx import Trx
        assert sender.asset == receiver.asset

        if int(amount * 10 ** AMOUNT_PRECISION) == 0 or sender == receiver:
            return

        self._trxs.append(Trx(
            sender=sender,
            receiver=receiver,
            amount=amount,
            scope=scope,
            group_id=group_id
        ))

        sender.balance -= amount
        receiver.balance += amount

        self._wallet_balances[sender.id] -= amount
        self._wallet_balances[receiver.id] += amount

    def _build_wallet_updates(self) -> dict:
        balances = sorted_flatten_dict(self._wallet_balances)
        locks = sorted_flatten_dict(self._wallet_locks)

        updates = defaultdict(dict)

        for wallet_id, balance in balances:
            if balance:
                updates[wallet_id]['balance'] = F('balance') + balance

        for wallet_id, lock in locks:
            if lock:
                updates[wallet_id]['locked'] = F('locked') + lock

        return updates

    def _build_lock_updates(self) -> dict:
        locks = sorted_flatten_dict(self._locks_amount)

        updates = defaultdict(dict)

        for lock_id, amount in locks:
            if amount:
                updates[lock_id]['amount'] = F('amount') + amount

        return updates

    def _execute(self):
        if self.verbose:
            print('wallet_update', self._build_wallet_updates())
            print('lock_update', self._build_lock_updates())
            print('new locks count', len(self._locks))
            print('new trxs', len(self._trxs))

        from ledger.models import Wallet, BalanceLock
        from ledger.models.trx import Trx

        for lock_id, lock_update in self._build_lock_updates().items():
            BalanceLock.objects.filter(key=lock_id).update(**lock_update)

        for wallet_id, wallet_update in sorted_flatten_dict(self._build_wallet_updates()):
            Wallet.objects.filter(id=wallet_id).update(**wallet_update)

        if self._trxs:
            Trx.objects.bulk_create(self._trxs)

        if self._locks:
            BalanceLock.objects.bulk_create(list(self._locks.values()))
