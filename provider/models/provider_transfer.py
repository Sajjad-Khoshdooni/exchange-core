import logging
from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q

from ledger.models import Asset, Network
from ledger.utils.fields import get_amount_field
from provider.exchanges import BinanceSpotHandler

logger = logging.getLogger(__name__)


class ProviderTransfer(models.Model):
    BINANCE = 'interface'

    created = models.DateTimeField(auto_now_add=True)

    exchange = models.CharField(max_length=8, default=BINANCE)

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    amount = get_amount_field()

    address = models.CharField(max_length=256)

    provider_transfer_id = models.CharField(max_length=64)
    caller_id = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_provider_transfer_amount', ), ]

    @classmethod
    def new_withdraw(cls, asset: Asset, network: Network, amount: Decimal, address: str, caller_id: str = '') -> 'ProviderTransfer':

        if ProviderTransfer.objects.filter(provider_transfer_id__isnull=False, caller_id=caller_id).exists():
            logger.warning('transfer ignored due to duplicated caller_id')
            return

        transfer = ProviderTransfer.objects.create(
            asset=asset, network=network, amount=amount, address=address, caller_id=caller_id
        )

        resp = BinanceSpotHandler.withdraw(
            coin=asset.symbol,
            network=network.symbol,
            address=address,
            amount=amount,
            client_id=transfer.id
        )

        transfer.provider_transfer_id = resp['id']
        transfer.save()

        return transfer

    def get_status(self) -> dict:
        data = BinanceSpotHandler.collect_api(
            '/sapi/v1/capital/withdraw/history', 'GET',
            data={'withdrawOrderId': self.id}
        )

        if not data:
            return

        data = data[0]

        return data

    def __str__(self):
        return '%s %s %s' % (self.asset, self.amount, self.network)
