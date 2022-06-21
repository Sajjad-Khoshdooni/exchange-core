import logging
import time
from decimal import Decimal

from django.conf import settings

from ledger.models import Transfer, Asset
from ledger.utils.price import BUY, get_price, SELL
from provider.models import ProviderTransfer, ProviderHedgedOrder

logger = logging.getLogger(__name__)


def handle_withdraw(transfer_id: int):
    if settings.DEBUG_OR_TESTING:
        return

    logger.info('withdraw handling transfer_id = %d' % transfer_id)

    transfer = Transfer.objects.get(id=transfer_id)
    handler = transfer.asset.get_hedger()

    if transfer.handling:
        logger.info('ignored because of handling flag')
        return

    try:
        transfer.handling = True
        transfer.save()

        assert not transfer.deposit
        assert transfer.source == transfer.BINANCE or transfer.KUCOIN
        assert transfer.status == transfer.PROCESSING
        assert not transfer.provider_transfer

        balance_map = handler.get_free_dict()

        coin = transfer.asset.symbol

        fee = handler.get_withdraw_fee(transfer.asset.symbol, transfer.network.symbol)
        amount = transfer.amount + fee

        if balance_map[coin] < amount:
            to_buy_amount = amount - balance_map[coin]

            logger.info('not enough %s in interface spot. So buy %s of it!' % (coin, to_buy_amount))

            if coin != Asset.USDT:
                to_buy_value = to_buy_amount * get_price(coin, side=SELL) * Decimal('1.002')
            else:
                to_buy_value = to_buy_amount

            if to_buy_value > balance_map[Asset.USDT]:
                raise Exception('insufficient balance in interface spot to full fill withdraw')

            if transfer.asset.symbol != Asset.USDT:
                ProviderHedgedOrder.new_hedged_order(
                    asset=transfer.asset,
                    amount=to_buy_amount,
                    spot_side=BUY,
                    caller_id=transfer.id
                )

                logger.info('waiting to finish buying...')
                time.sleep(1)

        balance_map = handler.get_free_dict()

        if balance_map[coin] < amount:
            logger.info('ignored withdrawing because of insufficient spot balance')
            return

        withdraw(transfer)

    finally:
        transfer.handling = False
        transfer.save()


def withdraw(transfer: Transfer):
    handler = transfer.asset.get_hedger()
    withdraw_fee = handler.get_withdraw_fee(transfer.wallet.asset.symbol, transfer.network.symbol)

    logger.info('withdrawing %s %s in %s network' % (withdraw_fee + transfer.amount, transfer.asset, transfer.network))

    provider_transfer = ProviderTransfer.new_withdraw(
        transfer.asset,
        transfer.network,
        transfer.amount,
        withdraw_fee,
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
