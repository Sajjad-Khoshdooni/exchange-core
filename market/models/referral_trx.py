import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models

from ledger.models import Trx, Asset, Wallet
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import floor_precision

logger = logging.getLogger(__name__)


class ReferralTrx(models.Model):
    REFERRER = 'referrer'
    TRADER = 'trader'

    created = models.DateTimeField(auto_now_add=True)

    referral = models.ForeignKey(
        to='accounts.Referral',
        on_delete=models.CASCADE,
    )

    group_id = models.UUIDField(default=uuid4, db_index=True)

    referrer_amount = get_amount_field()
    trader_amount = get_amount_field()

    @classmethod
    def init_trx(cls, trx_type: str, fee_trx, trade_price: Decimal, tether_factor: Decimal):
        if not fee_trx or not fee_trx.amount:
            return

        referral = fee_trx.sender.account.referral
        if not referral:
            return

        share_factor = (referral.owner_share_percent / Decimal(100)) if trx_type == cls.REFERRER else (
                    (100 - referral.owner_share_percent) / Decimal(100))

        irt_asset = Asset.get(symbol=Asset.IRT)
        system_wallet = irt_asset.get_wallet(fee_trx.receiver.account, Wallet.SPOT)
        receiver = irt_asset.get_wallet(fee_trx.sender.account, Wallet.SPOT) if trx_type == ReferralTrx.TRADER \
            else irt_asset.get_wallet(fee_trx.sender.account.referral.owner, Wallet.SPOT)

        if fee_trx.sender.asset.symbol in (Asset.IRT, Asset.USDT):
            amount = fee_trx.amount * tether_factor
        else:
            amount = fee_trx.amount * trade_price * tether_factor

        return Trx(
            sender=system_wallet,
            receiver=receiver,
            amount=floor_precision(amount * share_factor),
            group_id=fee_trx.group_id,
            scope=Trx.COMMISSION
        )
