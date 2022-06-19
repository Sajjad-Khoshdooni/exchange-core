from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import F

from ledger.models import Wallet, BalanceLock
from ledger.models.trx import Trx


def sorted_flatten_dict(data: dict) -> list:
    if not data:
        return []

    return sorted(data.items(), key=lambda x: x[0])


class WalletUpdater:
    def __init__(self, instant: bool = False):
        self._instant = instant
        self._executed = False

        self._wallet_locks = defaultdict(Decimal)
        self._wallet_balances = defaultdict(Decimal)

        self._trxs = []

        self._locks = []
        self._locks_amount = defaultdict(Decimal)

    def new_lock(self, key: UUID, wallet: Wallet, amount: Decimal):
        assert amount > 0
        if not wallet.should_update_balance_fields():
            return

        lock = BalanceLock(
            key=key,
            wallet=wallet,
            amount=amount,
            original_amount=amount
        )

        self._locks.append(lock)
        self._wallet_locks[wallet.id] += amount

        self._execute_if_instant()

    def release_lock(self, key: UUID, amount: Decimal = None):
        assert amount is None or amount >= 0

        lock = BalanceLock.objects.get(key=key)

        if not lock.wallet.should_update_balance_fields():
            return

        if amount is None:
            amount = lock.amount

        self._locks_amount[key] -= amount
        self._wallet_locks[lock.wallet_id] -= amount

        self._execute_if_instant()

    def new_trx(self, sender: Wallet, receiver: Wallet, amount: Decimal, scope: str, group_id: UUID):
        self._trxs.append(Trx(
            sender=sender,
            receiver=receiver,
            amount=amount,
            scope=scope,
            group_id=group_id
        ))

        self._wallet_balances[sender.id] -= amount
        self._wallet_balances[receiver.id] += amount

        self._execute_if_instant()

    def _build_wallet_updates(self) -> dict:
        balances = sorted_flatten_dict(self._wallet_balances)
        locks = sorted_flatten_dict(self._wallet_locks)

        updates = defaultdict(dict)

        for wallet_id, balance in balances:
            updates[wallet_id]['balance'] = F('balance') + balance

        for wallet_id, lock in locks:
            updates[wallet_id]['balance'] = F('locked') + lock

        return updates

    def _build_lock_updates(self) -> dict:
        locks = sorted_flatten_dict(self._locks_amount)

        updates = defaultdict(dict)

        for lock_id, amount in locks:
            updates[lock_id]['amount'] = F('amount') + amount

        return updates

    def execute(self):
        assert not self._executed

        with transaction.atomic():
            for wallet_id, wallet_update in sorted_flatten_dict(self._build_wallet_updates()):
                Wallet.objects.filter(id=wallet_id).update(**wallet_update)

            for lock_id, lock_update in self._build_lock_updates().items():
                BalanceLock.objects.filter(id=lock_id).update(**lock_update)

            if self._trxs:
                Trx.objects.bulk_create(self._trxs)

            if self._locks:
                BalanceLock.objects.bulk_create(self._locks)

        self._executed = True

    def _execute_if_instant(self):
        if self._instant:
            self.execute()
