from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.db.models import F, Sum
from django.utils import timezone

from accounts.models import Referral
from ledger.models import Wallet, Trx, Asset
from ledger.utils.cache import cache_for
from ledger.utils.external_price import BUY, SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, Trade, BaseTrade, PairSymbol
from market.models import ReferralTrx
from market.utils.price import get_symbol_prices


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


def register_transactions(pipeline: WalletPipeline, pair: TradesPair, fake_trade: bool = False):
    if not fake_trade:
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


def get_markets_change_percent(base: str):
    prices = get_symbol_prices()
    recent_prices = prices['last']
    yesterday_prices = prices['yesterday']
    change_percents = {}
    for pair_symbol_id in recent_prices.keys() & yesterday_prices.keys():
        if recent_prices[pair_symbol_id] and yesterday_prices[pair_symbol_id] and PairSymbol.objects.get(
                pair_symbol_id).base_asset.symbol == base:
            yesterday_price = yesterday_prices[pair_symbol_id]
            recent_price = recent_prices[pair_symbol_id]
            change_percent = 100 * (recent_price - yesterday_price) // yesterday_price
            change_percents[PairSymbol.objects.get(pair_symbol_id).name] = change_percent

    return change_percents


def get_market_size_ratio(base: str):
    qs = Trade.objects.filter(
        status=Trade.DONE,
        created__gte=timezone.now() - timedelta(days=1),
        symbol__base_asset__symbol=base
    )

    total_size = qs.annotate(value=F('amount') * F('price')).aggregate(
        total_size=Sum('value')
    ).get('total_size', 0)

    if not total_size or total_size == 0:
        return {}

    total_size = Decimal(total_size)

    return qs.values('symbol__name').annotate(
        ratio=F('amount') * F('price') / total_size,
    ).values('symbol__name', 'ratio')


@cache_for(60 * 5)
def get_markets_info(base: str):
    change_percents = get_markets_change_percent(base)

    market_ratios = get_market_size_ratio(base)

    print(market_ratios, '\n', change_percents)

    market_details = {
        market: [ratio, change_percents.get(market, 0)]
        for market, ratio in market_ratios
        if market and ratio and change_percents.get(market)
    }

    return market_details
