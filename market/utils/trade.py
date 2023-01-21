from dataclasses import dataclass
from decimal import Decimal
from typing import Union
from uuid import UUID

from django.conf import settings

from ledger.models import Wallet, Trx, Asset
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, Trade
from market.models import ReferralTrx


@dataclass
class TradesPair:
    maker_trade: Trade
    taker_trade: Trade
    maker_order: Order
    taker_order: Order

    @property
    def trades(self):
        return [self.maker_trade, self.taker_trade]

    @classmethod
    def init_pair(cls, maker_order: Order, taker_order: Order, amount: Decimal, price: Decimal, trade_source: str,
                  base_irt_price: Decimal, base_usdt_price: Decimal, group_id: UUID):

        assert maker_order.symbol == taker_order.symbol

        maker_trade = Trade(
            symbol=maker_order.symbol,
            order_id=maker_order.id,
            account=maker_order.wallet.account,
            side=maker_order.side,
            is_maker=True,
            trade_source=trade_source,
            amount=amount,
            price=price,
            base_irt_price=base_irt_price,
            base_usdt_price=base_usdt_price,
            group_id=group_id
        )

        taker_trade = Trade(
            symbol=maker_order.symbol,
            order_id=taker_order.id,
            account=taker_order.wallet.account,
            side=taker_order.side,
            is_maker=False,
            trade_source=trade_source,
            amount=amount,
            price=price,
            base_irt_price=base_irt_price,
            base_usdt_price=base_usdt_price,
            group_id=group_id
        )

        return TradesPair(
            maker_trade=maker_trade,
            taker_trade=taker_trade,
            maker_order=maker_order,
            taker_order=taker_order,
        )


def register_transactions(pipeline: WalletPipeline, pair: TradesPair, fake_trade: bool = False):

    if not fake_trade:
        _register_trade_transaction(pipeline, pair=pair)
        _register_trade_base_transaction(pipeline, pair=pair)

    pair.taker_trade.fee_amount = _register_fee_transaction(pipeline, pair.taker_order, pair.taker_trade)
    pair.maker_trade.fee_amount = _register_fee_transaction(pipeline, pair.maker_order, pair.maker_trade)


def _register_trade_transaction(pipeline: WalletPipeline, pair: TradesPair):

    if pair.maker_order.side == Order.BUY:
        sender, receiver = pair.taker_order.wallet, pair.maker_order.wallet
    else:
        sender, receiver = pair.maker_order.wallet, pair.taker_order.wallet

    pipeline.new_trx(
        sender=sender,
        receiver=receiver,
        amount=pair.maker_trade.amount,
        group_id=pair.maker_trade.group_id,
        scope=Trx.TRADE
    )


def _register_trade_base_transaction(pipeline: WalletPipeline, pair: TradesPair):
    if pair.maker_order.side == Order.SELL:
        sender, receiver = pair.taker_order.base_wallet, pair.maker_order.base_wallet
    else:
        sender, receiver = pair.maker_order.base_wallet, pair.taker_order.base_wallet

    pipeline.new_trx(
        sender=sender,
        receiver=receiver,
        amount=pair.maker_trade.amount * pair.maker_trade.price,
        group_id=pair.maker_trade.group_id,
        scope=Trx.TRADE
    )


def _register_fee_transaction(pipeline: WalletPipeline, order: Order, trade: Trade) -> Decimal:
    account = order.wallet.account
    fee_rate = order.symbol.get_maker_fee(account) if trade.is_maker else order.symbol.get_taker_fee(account)

    fee_payer = order.wallet if order.side == Order.BUY else order.base_wallet
    fee_amount = initial_fee_amount = fee_rate * trade.amount * (1 if order.side == Order.BUY else trade.price)

    if not initial_fee_amount:
        return Decimal()

    referrer = order.wallet.account.referred_by
    if referrer:
        referrer_share_percent = min(max(referrer.owner_share_percent, 0), 30)
        trader_share_percent = ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - referrer_share_percent

        fee_amount *= 1 - Decimal(trader_share_percent) / 100

        referrer_reward = initial_fee_amount * Decimal(referrer_share_percent) / 100
        if referrer_reward:
            irt_asset = Asset.get(symbol=Asset.IRT)
            referrer_reward_irt = referrer_reward * trade.base_irt_price

            if trade.side == Order.BUY:
                referrer_reward_irt *= trade.price

            # referrer reward trx
            pipeline.new_trx(
                sender=irt_asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_payer.market),
                receiver=irt_asset.get_wallet(referrer.owner, Wallet.SPOT),
                amount=referrer_reward_irt,
                group_id=trade.group_id,
                scope=Trx.COMMISSION
            )
            ReferralTrx.objects.create(
                trader=order.wallet.account,
                referral=referrer,
                group_id=trade.group_id,
                trader_amount=0,
                referrer_amount=referrer_reward_irt
            )

    # fee trx
    pipeline.new_trx(
        sender=fee_payer,
        receiver=fee_payer.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_payer.market),
        amount=fee_amount,
        group_id=trade.group_id,
        scope=Trx.COMMISSION
    )

    return fee_amount
