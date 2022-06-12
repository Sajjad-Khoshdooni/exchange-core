import logging
from decimal import Decimal

from django.db import models
from yekta_config.config import config

from accounts.models import Account
from ledger.consts import DEFAULT_COIN_OF_NETWORK
from ledger.crypto_account_balance_getter import CryptoAccountBalanceGetterFactory
from ledger.models import Transfer
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_trading_price_usdt, BUY

logger = logging.getLogger(__name__)


class CryptoBalance(models.Model):
    amount = get_amount_field(default=Decimal(0))
    deposit_address = models.ForeignKey('ledger.DepositAddress', on_delete=models.PROTECT)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('deposit_address', 'asset')

    def __str__(self):
        return '%s %s %f' % (self.asset, self.deposit_address, self.amount)

    def update(self):
        balance = CryptoAccountBalanceGetterFactory.build(self.deposit_address.network).get_asset_of_account(
            self.deposit_address, self.asset
        )
        self.amount = balance
        self.save()

    def get_value(self):
        return self.amount * get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)

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

    def collect(self):
        from ledger.withdraw.fee_handler import FeeHandler

        binance_network_addresses = {
            'TRX': config('HOT_WALLET_TRX_ADDRESS'),
            'BSC': config('HOT_WALLET_BSC_ADDRESS')
        }

        network = self.deposit_address.network

        if Transfer.objects.filter(
                status__in=[Transfer.PROCESSING, Transfer.PENDING],
                deposit=False,
                source=Transfer.SELF,
                deposit_address=self.deposit_address
            ):
            logger.info('ignoring transfer due to already alive transfer')
            return

        coin = self.asset.symbol
        base_coin = DEFAULT_COIN_OF_NETWORK[network.symbol]

        fee_amount = FeeHandler(network, self.asset).get_asset_fee()

        if coin == base_coin:
            amount = self.amount - fee_amount
        else:
            amount = self.amount

        value = amount * get_trading_price_usdt(coin=coin, side=BUY, raw_price=True)
        fee_value = fee_amount * get_trading_price_usdt(base_coin, side=BUY, raw_price=True)

        if value <= fee_value * 2:
            logger.info('ignoring crypto = %d for small value' % self.id)
            return

        address = binance_network_addresses[self.deposit_address.network.symbol]
        self.send_to(address, amount)

    @classmethod
    def collect_all(cls, exclude_base_assets: bool = True):
        all_crypto = CryptoBalance.objects.filter(
            amount__gt=0
        ).exclude(
            deposit_address__account_secret__account=Account.system()
        )

        for crypto in all_crypto:
            coin = crypto.asset.symbol
            base_coin = DEFAULT_COIN_OF_NETWORK[crypto.deposit_address.network.symbol]

            if exclude_base_assets and coin == base_coin:
                logger.info('ignoring base asset transfer')
                continue

            crypto.collect()
