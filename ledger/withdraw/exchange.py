import logging
import time
from decimal import Decimal

from django.conf import settings

from ledger.models import Transfer, Asset
from ledger.utils.price import BUY, get_price, SELL
from ledger.utils.provider import get_provider_requester, BINANCE

logger = logging.getLogger(__name__)


def handle_provider_withdraw(transfer_id: int):
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return

    logger.info('withdraw handling transfer_id = %d' % transfer_id)

    transfer = Transfer.objects.get(id=transfer_id)

    if transfer.handling:
        logger.info('ignored because of handling flag')
        return

    try:
        transfer.handling = True
        transfer.save(update_fields=['handling'])

        assert not transfer.deposit
        assert transfer.source == Transfer.PROVIDER
        assert transfer.status == transfer.PROCESSING
        assert not transfer.provider_transfer

        coin = transfer.asset.symbol

        requester = get_provider_requester()

        balance_map = requester.get_spot_balance_map(BINANCE)
        network_info = requester.get_network_info(transfer.asset, transfer.network)

        fee = network_info.withdraw_fee
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
                # todo: handle this!
                # prev_hedge = ProviderHedgedOrder.objects.filter(caller_id=transfer.id).first()
                #
                # if prev_hedge and prev_hedge.created < timezone.now() - timedelta(minutes=5):
                #     prev_hedge.caller_id = prev_hedge.caller_id + 'a'
                #     prev_hedge.save(update_fields=['caller_id'])

                get_provider_requester().new_hedged_spot_buy(
                    asset=transfer.asset,
                    amount=to_buy_amount,
                    spot_side=BUY,
                    caller_id=transfer.id
                )

                logger.info('waiting to finish buying...')
                time.sleep(1)

        balance_map = requester.get_spot_balance_map(BINANCE)

        if Decimal(balance_map[coin]) < amount:
            logger.info('ignored withdrawing because of insufficient spot balance')
            return

        provider_withdraw(transfer)

    finally:
        transfer.handling = False
        transfer.save(update_fields=['handling'])


def provider_withdraw(transfer: Transfer):
    assert transfer.source == Transfer.PROVIDER

    success = get_provider_requester().new_withdraw(transfer)

    if not success:
        return

    transfer.status = transfer.PENDING
    transfer.save(update_fields=['status'])
