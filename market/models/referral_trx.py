import logging
from collections import namedtuple
from decimal import Decimal
from uuid import uuid4

from django.db import models
from django.db.models import CheckConstraint, Q

from ledger.models import Trx, Asset, Wallet
from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


class ReferralTrx(models.Model):
    REFERRAL_MAX_RETURN_PERCENT = 30

    REFERRER = 'referrer'
    TRADER = 'trader'

    created = models.DateTimeField(auto_now_add=True)

    referral = models.ForeignKey(
        to='accounts.Referral',
        on_delete=models.CASCADE,
    )
    trader = models.ForeignKey(
        to='accounts.Account',
        on_delete=models.CASCADE,
    )

    group_id = models.UUIDField(default=uuid4, db_index=True)

    referrer_amount = get_amount_field()
    trader_amount = get_amount_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trx_dict = None

    @staticmethod
    def get_trade_referrals(maker_fee, taker_fee, trade_price, tether_irt, is_buyer_maker: bool):
        irt_asset = Asset.get(symbol=Asset.IRT)
        maker_referral = ReferralTrx().init_trx(
            maker_fee, trade_price, tether_irt, irt_asset=irt_asset, sell=not is_buyer_maker
        )
        taker_referral = ReferralTrx().init_trx(
            taker_fee, trade_price, tether_irt, irt_asset=irt_asset, sell=is_buyer_maker
        )

        TradeReferral = namedtuple("TradeReferral", "maker taker")
        return TradeReferral(maker_referral, taker_referral)

    def init_trx(self, fee_trx, trade_price: Decimal, tether_factor: Decimal, sell: bool, irt_asset=None):
        if not fee_trx or not fee_trx.amount:
            return

        referral = fee_trx.sender.account.referred_by
        if not referral:
            return

        if not irt_asset:
            irt_asset = Asset.get(symbol=Asset.IRT)
        system_wallet = irt_asset.get_wallet(fee_trx.receiver.account, Wallet.SPOT)

        real_fee_amount = fee_trx.amount * (Decimal(100) / (Decimal(100) - (
                    Decimal(ReferralTrx.REFERRAL_MAX_RETURN_PERCENT) - Decimal(referral.owner_share_percent))))
        if sell:
            amount = real_fee_amount * tether_factor
        else:
            amount = real_fee_amount * trade_price * tether_factor

        self.trx_dict = {}
        for receiver_type in [self.TRADER, self.REFERRER]:
            self.trx_dict[receiver_type] = Trx.transaction(
                sender=system_wallet,
                receiver=self.get_receiver(irt_asset, fee_trx, receiver_type),
                amount=amount * self.get_share_factor(referral, receiver_type),
                group_id=fee_trx.group_id,
                scope=Trx.COMMISSION
            )

        if self.trx_dict[ReferralTrx.TRADER]:
            self.trader = self.trx_dict[ReferralTrx.TRADER].receiver.account
            self.referral = self.trx_dict[ReferralTrx.TRADER].receiver.account.referred_by
            self.group_id = self.trx_dict[ReferralTrx.TRADER].group_id
            self.trader_amount = self.trx_dict[ReferralTrx.TRADER].amount
            self.referrer_amount = self.trx_dict[ReferralTrx.REFERRER].amount
            if self.trader_amount or self.referrer_amount:
                return self

    @staticmethod
    def get_receiver(irt_asset, fee_trx, receiver_type):
        if receiver_type == ReferralTrx.TRADER:
            return irt_asset.get_wallet(fee_trx.sender.account, Wallet.SPOT)
        else:
            return irt_asset.get_wallet(fee_trx.sender.account.referred_by.owner, Wallet.SPOT)

    @classmethod
    def get_share_factor(cls, referral, receiver_type):
        assert 0 <= referral.owner_share_percent <= cls.REFERRAL_MAX_RETURN_PERCENT

        if receiver_type == ReferralTrx.TRADER:
            return Decimal(0)
        else:
            return Decimal(referral.owner_share_percent) / 100

    @staticmethod
    def get_trx_list(referrals):
        trx_list = []
        if referrals.maker and referrals.maker.trx_dict:
            trx_list.extend(referrals.maker.trx_dict.values())
        if referrals.taker and referrals.taker.trx_dict:
            trx_list.extend(referrals.taker.trx_dict.values())
        return trx_list

    class Meta:
        constraints = [
            CheckConstraint(check=Q(referrer_amount__gte=0, trader_amount__gte=0), name='check_market_referraltrx_amounts', ),
        ]
