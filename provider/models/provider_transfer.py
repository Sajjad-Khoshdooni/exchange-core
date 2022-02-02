from decimal import Decimal

from django.db import models, transaction

from ledger.models import Asset, Network
from ledger.utils.fields import get_amount_field
from provider.exchanges import BinanceSpotHandler


class ProviderTransfer(models.Model):
    BINANCE = 'binance'

    created = models.DateTimeField(auto_now_add=True)

    exchange = models.CharField(max_length=8, default=BINANCE)

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    amount = get_amount_field()

    address = models.CharField(max_length=256)

    provider_transfer_id = models.CharField(max_length=64)

    @classmethod
    def new_withdraw(cls, asset: Asset, network: Network, amount: Decimal, address: str) -> 'ProviderTransfer':
        with transaction.atomic():
            transfer = ProviderTransfer.objects.create(
                asset=asset, network=network, amount=amount, address=address
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

    def get_status(self):
        data = BinanceSpotHandler.collect_api(
            '/sapi/v1/capital/withdraw/history', 'GET',
            data={'withdrawOrderId': self.id}
        )

        if not data:
            return

        data = data[0]

        if 'txId' in data:
            tx_id = data['txId']

        status = data['status']
        description = ''
        if status % 2 == 1:
            transfer.status = AssetTransfer.CANCELED
        elif status == 6:
            transfer.withdraw_done = True
        else:
            description = 'withdraw pending with status %s' % status

