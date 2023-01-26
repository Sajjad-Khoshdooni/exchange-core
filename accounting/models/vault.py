import dataclasses
from datetime import datetime
from decimal import Decimal
from typing import List

from django.db import models
from simple_history.models import HistoricalRecords

from ledger.utils.fields import get_amount_field


@dataclasses.dataclass
class VaultData:
    coin: str
    balance: Decimal
    value_usdt: Decimal
    value_irt: Decimal


class Vault(models.Model):
    TYPES = PROVIDER, GATEWAY, HOT_WALLET, COLD_WALLET, MANUAL = 'provider', 'gateway', 'hw', 'cw', 'manual'
    MARKETS = SPOT, FUTURES = 'spot', 'futures'

    name = models.CharField(max_length=32)
    type = models.CharField(max_length=8, choices=[(t, t) for t in TYPES])
    market = models.CharField(max_length=8, choices=[(t, t) for t in MARKETS], default=SPOT)

    key = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.name + ' ' + self.type

    class Meta:
        unique_together = ('key', 'type', 'market')

    def update_vault_all_items(self, now, data: List[VaultData]):
        coins = []

        for vd in data:
            if vd.balance > 0:
                VaultItem.objects.update_or_create(
                    vault=self,
                    coin=vd.coin,
                    defaults={
                        'updated': now,
                        'balance': vd.balance,
                        'value_usdt': vd.value_usdt,
                        'value_irt': vd.value_irt
                    }
                )

                coins.append(vd.coin)

        VaultItem.objects.filter(vault=self).exclude(coin=coins).update(
            balance=0,
            value_usdt=0,
            value_irt=0,
            updated=now,
        )


class VaultItem(models.Model):
    history = HistoricalRecords()

    updated = models.DateTimeField(auto_now=True)

    vault = models.ForeignKey(Vault, on_delete=models.CASCADE)
    coin = models.CharField(max_length=32, db_index=True)
    balance = get_amount_field()
    value_usdt = get_amount_field()
    value_irt = get_amount_field()

    class Meta:
        unique_together = ('vault', 'coin')

    def __str__(self):
        return '%s %s' % (self.vault, self.coin)
