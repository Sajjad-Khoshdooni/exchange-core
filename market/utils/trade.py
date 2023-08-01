from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.conf import settings

from accounts.models import Referral
from ledger.models import Wallet, Trx, Asset
from ledger.utils.external_price import BUY, SELL
from ledger.utils.precision import floor_precision
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, Trade, BaseTrade
from market.models import ReferralTrx


@dataclass
class FeeInfo:
    trader_fee_amount: Decimal = 0
    trader_fee_value: Decimal = 0
    referrer_reward_irt: Decimal = 0
    fee_revenue: Decimal = 0


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
            login_activity=maker_order.login_activity,
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
            login_activity=taker_order.login_activity,
        )
        maker_trade.client_order_id = maker_order.client_order_id
        taker_trade.client_order_id = taker_order.client_order_id

        return TradesPair(
            maker_trade=maker_trade,
            taker_trade=taker_trade,
            maker_order=maker_order,
            taker_order=taker_order,
        )


def _update_trading_positions(trading_positions, pipeline):
    from ledger.models import MarginLoan
    from ledger.models import MarginPosition
    to_update_positions = {}
    for trade_info in trading_positions:
        position = to_update_positions.get(trade_info.position.id, trade_info.position)
        short_amount = trade_info.trade_amount if trade_info.loan_type == MarginLoan.BORROW else -trade_info.trade_amount
        previous_amount, previous_price = position.amount, position.average_price
        position.amount += short_amount
        if short_amount > 0:
            position.average_price = (previous_amount * previous_price +
                                      short_amount * trade_info.trade_price) / position.amount
        position.update_liquidation_price(pipeline)
        to_update_positions[position.id] = position
        if position.amount == 0:
            position.status = MarginPosition.CLOSED
            margin_cross_wallet = position.margin_base_wallet.asset.get_wallet(
                position.account, market=Wallet.MARGIN, variant=None)
            remaining_balance = position.margin_base_wallet.balance + pipeline.get_wallet_balance_diff(
                position.margin_base_wallet.id)
            if remaining_balance:
                pipeline.new_trx(
                    position.margin_base_wallet, margin_cross_wallet, remaining_balance, Trx.MARGIN_TRANSFER,
                    trade_info.group_id
                )

    MarginPosition.objects.bulk_update(
        to_update_positions.values(), ['amount', 'average_price', 'liquidation_price', 'status']
    )


def register_transactions(pipeline: WalletPipeline, pair: TradesPair, fake_trade: bool = False):
    trading_positions = []
    if not fake_trade:
        trading_positions = _register_borrow_transaction(pipeline, pair=pair)
        _register_trade_transaction(pipeline, pair=pair)
        _register_trade_base_transaction(pipeline, pair=pair)

    taker_fee = register_fee_transactions(
        pipeline=pipeline,
        trade=pair.taker_trade,
        wallet=pair.taker_order.wallet,
        base_wallet=pair.taker_order.base_wallet,
        group_id=pair.taker_trade.group_id
    )

    pair.taker_trade.fee_amount = taker_fee.trader_fee_amount
    pair.taker_trade.fee_usdt_value = taker_fee.trader_fee_amount
    pair.taker_trade.fee_revenue = taker_fee.fee_revenue

    maker_fee = register_fee_transactions(
        pipeline=pipeline,
        trade=pair.maker_trade,
        wallet=pair.maker_order.wallet,
        base_wallet=pair.maker_order.base_wallet,
        group_id=pair.maker_trade.group_id
    )

    pair.maker_trade.fee_amount = maker_fee.trader_fee_amount
    pair.maker_trade.fee_usdt_value = maker_fee.trader_fee_amount
    pair.maker_trade.fee_revenue = maker_fee.fee_revenue

    if not fake_trade:
        trading_positions.extend(_register_repay_transaction(pipeline, pair=pair))
        _update_trading_positions(trading_positions, pipeline)


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


def _register_margin_transaction(pipeline: WalletPipeline, pair: TradesPair, loan_type: str):
    from ledger.models import MarginLoan
    if loan_type == MarginLoan.BORROW:
        order_side = SELL
    elif loan_type == MarginLoan.REPAY:
        order_side = BUY
    else:
        raise ValueError

    trade_price = pair.maker_trade.price
    trading_positions = []
    for order, trade in ((pair.maker_order, pair.maker_trade), (pair.taker_order, pair.taker_trade)):
        if order.side == order_side and order.wallet.market == Wallet.MARGIN:
            trade_amount = trade.amount - trade.fee_amount if order_side == BUY else trade.amount
            from ledger.models import MarginLoan
            position = order.symbol.get_margin_position(order.account)
            if loan_type == MarginLoan.REPAY:
                trade_amount = min(position.amount, trade_amount)
            MarginLoan.new_loan(
                account=order.account,
                asset=order.symbol.asset,
                amount=trade_amount,
                loan_type=loan_type,
                pipeline=pipeline,
                variant=order.wallet.variant
            )
            fee_amount = floor_precision(trade.fee_amount,
                                         Trade.fee_amount.field.decimal_places) if trade.fee_amount else Decimal(0)
            trade_amount = trade.amount - fee_amount if order_side == BUY else trade.amount
            if loan_type == MarginLoan.REPAY:
                trade_amount = min(position.amount, trade_amount)
            from ledger.models.position import MarginPositionTradeInfo
            trading_positions.append(MarginPositionTradeInfo(
                loan_type=loan_type,
                position=position,
                trade_amount=trade_amount,
                trade_price=trade_price,
                group_id=order.group_id
            ))
    return trading_positions


def _register_borrow_transaction(pipeline: WalletPipeline, pair: TradesPair):
    from ledger.models import MarginLoan
    return _register_margin_transaction(pipeline, pair, MarginLoan.BORROW)


def _register_repay_transaction(pipeline: WalletPipeline, pair: TradesPair):
    from ledger.models import MarginLoan
    return _register_margin_transaction(pipeline, pair, MarginLoan.REPAY)


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


def get_fee_info(trade: BaseTrade) -> FeeInfo:
    account = trade.account
    fee_rate = trade.symbol.get_fee_rate(account, trade.is_maker)

    if not fee_rate:
        return FeeInfo()

    referrer = account.referred_by
    base_amount = trade.amount * trade.price

    referrer_reward = 0
    trader_fee_rate = fee_rate
    system_fee_rate = fee_rate

    if referrer:
        referrer_share_percent = min(max(referrer.owner_share_percent, 0), 30)
        trader_share_percent = Referral.REFERRAL_MAX_RETURN_PERCENT - referrer_share_percent

        trader_fee_rate *= (1 - Decimal(trader_share_percent) / 100)
        referrer_reward = base_amount * fee_rate * Decimal(referrer_share_percent) / 100
        system_fee_rate *= (1 - Decimal(Referral.REFERRAL_MAX_RETURN_PERCENT) / 100)

    return FeeInfo(
        trader_fee_amount=trader_fee_rate * (trade.amount if trade.side == BUY else base_amount),
        trader_fee_value=trader_fee_rate * base_amount * trade.base_usdt_price,
        referrer_reward_irt=referrer_reward * trade.base_irt_price,
        fee_revenue=system_fee_rate * base_amount * trade.base_usdt_price,
    )


def register_fee_transactions(pipeline: WalletPipeline, trade: BaseTrade, wallet: Wallet, base_wallet: Wallet,
                              group_id: UUID) -> FeeInfo:
    account = trade.account
    referrer = account.referred_by
    fee_info = get_fee_info(trade)
    fee_payer = wallet if trade.side == BUY else base_wallet

    if fee_info.referrer_reward_irt:
        irt_asset = Asset.get(symbol=Asset.IRT)
        pipeline.new_trx(
            sender=irt_asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_payer.market),
            receiver=irt_asset.get_wallet(referrer.owner, Wallet.SPOT),
            amount=fee_info.referrer_reward_irt,
            group_id=group_id,
            scope=Trx.COMMISSION
        )
        ReferralTrx.objects.create(
            trader=wallet.account,
            referral=referrer,
            group_id=group_id,
            trader_amount=0,
            referrer_amount=fee_info.referrer_reward_irt
        )

    pipeline.new_trx(
        sender=fee_payer,
        receiver=fee_payer.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_payer.market),
        amount=fee_info.trader_fee_amount,
        group_id=group_id,
        scope=Trx.COMMISSION
    )

    return fee_info
