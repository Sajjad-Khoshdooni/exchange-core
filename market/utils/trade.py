from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.conf import settings

from accounts.models import Account, Referral
from ledger.models import Wallet, Trx, Asset
from ledger.utils.external_price import BUY, SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, Trade, BaseTrade
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
            group_id=group_id,
            market=maker_order.wallet.market,
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
            group_id=group_id,
            market=taker_order.wallet.market,
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

    pair.taker_trade.fee_amount = _register_fee_transaction(
        pipeline=pipeline,
        trade=pair.taker_trade,
        wallet=pair.taker_order.wallet,
        base_wallet=pair.taker_order.base_wallet,
        group_id=pair.taker_trade.group_id
    )
    pair.taker_trade.fee_usdt_value = (pair.taker_trade.price if pair.taker_order.side == BUY else 1) * pair.taker_trade.base_usdt_price

    pair.maker_trade.fee_amount = _register_fee_transaction(
        pipeline=pipeline,
        trade=pair.maker_trade,
        wallet=pair.maker_order.wallet,
        base_wallet=pair.maker_order.base_wallet,
        group_id=pair.maker_trade.group_id
    )
    pair.maker_trade.fee_usdt_value = (pair.maker_trade.price if pair.maker_order.side == BUY else 1) * pair.maker_trade.base_usdt_price


def _register_trade_transaction(pipeline: WalletPipeline, pair: TradesPair):

    if pair.maker_order.side == BUY:
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
    if pair.maker_order.side == SELL:
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


def get_trader_fee(trade: BaseTrade) -> Decimal:
    account = trade.account
    referrer = account.referred_by
    fee_rate = trade.symbol.get_fee_rate(account, trade.is_maker)

    if referrer:
        referrer_share_percent = min(max(referrer.owner_share_percent, 0), 30)
        trader_share_percent = Referral.REFERRAL_MAX_RETURN_PERCENT - referrer_share_percent

        fee_rate *= (1 - Decimal(trader_share_percent) / 100)

    return fee_rate * trade.amount * (1 if trade.side == BUY else trade.price)


def get_referrer_reward(account: Account, trade_value: Decimal, fee_rate: Decimal) -> Decimal:
    referrer = account.referred_by

    if not referrer:
        return Decimal()

    referrer_share_percent = min(max(referrer.owner_share_percent, 0), 30)

    return trade_value * fee_rate * Decimal(referrer_share_percent) / 100


def _register_fee_transaction(pipeline: WalletPipeline, trade: BaseTrade, wallet: Wallet, base_wallet: Wallet,
                              group_id: UUID) -> Decimal:

    account = trade.account
    fee_rate = trade.symbol.get_fee_rate(account, trade.is_maker)

    fee_payer = wallet if trade.side == BUY else base_wallet
    initial_fee_amount = fee_rate * trade.amount * (1 if trade.side == BUY else trade.price)

    trader_fee = get_trader_fee(trade)

    if not initial_fee_amount:
        return Decimal()

    referrer = trade.account.referred_by
    if referrer:
        referrer_share_percent = min(max(referrer.owner_share_percent, 0), 30)

        referrer_reward = initial_fee_amount * Decimal(referrer_share_percent) / 100
        if referrer_reward:
            irt_asset = Asset.get(symbol=Asset.IRT)
            referrer_reward_irt = referrer_reward * trade.base_irt_price

            if trade.side == BUY:
                referrer_reward_irt *= trade.price

            # referrer reward trx
            pipeline.new_trx(
                sender=irt_asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_payer.market),
                receiver=irt_asset.get_wallet(referrer.owner, Wallet.SPOT),
                amount=referrer_reward_irt,
                group_id=group_id,
                scope=Trx.COMMISSION
            )
            ReferralTrx.objects.create(
                trader=wallet.account,
                referral=referrer,
                group_id=group_id,
                trader_amount=0,
                referrer_amount=referrer_reward_irt
            )

    # fee trx
    pipeline.new_trx(
        sender=fee_payer,
        receiver=fee_payer.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_payer.market),
        amount=trader_fee,
        group_id=group_id,
        scope=Trx.COMMISSION
    )

    return trader_fee
