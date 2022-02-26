import logging
from decimal import Decimal

from django.db import models

from accounts.models import Account
from ledger.consts import DEFAULT_COIN_OF_NETWORK
from ledger.crypto_account_balance_getter import CryptoAccountBalanceGetterFactory
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_trading_price_usdt, BUY
from ledger.withdraw.fee_handler import FeeHandler

logger = logging.getLogger(__name__)


class CryptoBalance(models.Model):
    amount = get_amount_field(default=Decimal(0))
    deposit_address = models.ForeignKey('ledger.DepositAddress', on_delete=models.PROTECT)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('deposit_address', 'asset')

    def update(self):
        balance = CryptoAccountBalanceGetterFactory.build(self.deposit_address.network).get_asset_of_account(
            self.deposit_address, self.asset
        )
        self.amount = balance
        self.save()

    def send_to(self, address: str, amount: Decimal):
        from ledger.models import Transfer
        from ledger.withdraw.withdraw_handler import WithdrawHandler

        wallet = self.asset.get_wallet(self.deposit_address.account)

        transfer = Transfer.objects.create(
            source=Transfer.SELF,
            deposit=False,
            network=self.deposit_address.network,
            wallet=wallet,
            deposit_address=self.deposit_address,
            amount=amount,
            out_address=address,
            hidden=True
        )

        WithdrawHandler.withdraw_from_transfer(transfer)

    @classmethod
    def collect_all(cls):
        binance_network_addresses = {
            'TRX': 'TWnBUM28vwaN2g4NWNf8VVphbXSe537SCv',
            'BSC': '0x4b6c77358c69ed0a3af7c1a1131560432b824d69'
        }

        all_crypto = CryptoBalance.objects.filter(
            amount__gt=0
        ).exclude(
            deposit_address__account_secret__account=Account.system()
        )

        for crypto in all_crypto:
            value = crypto.amount * get_trading_price_usdt(coin=crypto.asset.symbol, side=BUY, raw_price=True)

            fee_amount = FeeHandler(crypto.deposit_address.network, crypto.asset).get_asset_fee()
            default_coin = DEFAULT_COIN_OF_NETWORK[crypto.deposit_address.network.symbol]

            fee_value = fee_amount * get_trading_price_usdt(default_coin, side=BUY, raw_price=True)

            if value <= fee_value * 2:
                logger.info('ignoring crypto = %d for small value' % crypto.id)
                continue

            address = binance_network_addresses[crypto.deposit_address.network.symbol]
            crypto.send_to(address, crypto.amount)
