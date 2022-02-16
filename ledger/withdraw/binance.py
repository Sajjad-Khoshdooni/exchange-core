import logging
from decimal import Decimal

from ledger.models import Transfer, Asset
from ledger.utils.price import BUY, get_price, SELL
from provider.exchanges import BinanceSpotHandler
from provider.models import ProviderTransfer, ProviderHedgedOrder

logger = logging.getLogger(__name__)


def handle_binance_withdraw(transfer_id: int):
    transfer = Transfer.objects.get(id=transfer_id)

    if transfer.handling:
        logger.info('ignored because of handling flag')
        return

    try:
        transfer.handling = True
        transfer.save()

        assert not transfer.deposit
        assert transfer.source == transfer.BINANCE
        assert transfer.status == transfer.PROCESSING
        assert not transfer.provider_transfer

        balances_list = BinanceSpotHandler.get_account_details()['balances']
        balance_map = {b['asset']: Decimal(b['free']) for b in balances_list}

        coin = transfer.asset.symbol

        binance_fee = BinanceSpotHandler.get_withdraw_fee(transfer.asset.symbol, transfer.network.symbol)
        amount = transfer.amount + binance_fee

        if balance_map[coin] < amount:
            to_buy_amount = amount - balance_map[coin]

            if coin != Asset.USDT:
                to_buy_value = to_buy_amount * get_price(coin, side=SELL) * 1.02
            else:
                to_buy_value = to_buy_amount

            if to_buy_value < balance_map[Asset.USDT]:
                raise Exception('Insufficient balance in binance spot to full fill withdraw')

            if transfer.asset.symbol != Asset.USDT:
                ProviderHedgedOrder.new_hedged_order(
                    asset=transfer.asset,
                    amount=to_buy_amount,
                    spot_side=BUY,
                    caller_id=transfer.id
                )

        withdraw(transfer)

    finally:
        transfer.handling = False
        transfer.save()


def withdraw(transfer: Transfer):
    binance_fee = BinanceSpotHandler.get_withdraw_fee(transfer.wallet.asset.symbol, transfer.network.symbol)

    provider_transfer = ProviderTransfer.new_withdraw(
        transfer.wallet.asset,
        transfer.network,
        transfer.amount + binance_fee,
        transfer.out_address,
        caller_id=str(transfer.id)
    )

    if not provider_transfer:
        logger.error(
            'creating provider transfer failed!'
        )
        return

    transfer.provider_transfer = provider_transfer
    transfer.status = transfer.PENDING
    transfer.save()
