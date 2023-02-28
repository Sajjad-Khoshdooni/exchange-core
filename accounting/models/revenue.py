from django.db import models

from ledger.models import Asset
from ledger.utils.external_price import BUY, get_external_price, get_other_side
from ledger.utils.fields import get_amount_field, get_group_id_field
from ledger.utils.otc import get_asset_spread, spread_to_multiplier, get_market_spread
from market.models import BaseTrade


class TradeRevenue(models.Model):
    """
    price = coin_price * base_price
    coin_price = coin_real_price * (1 +- coin_spread)
    base_price = base_real_price * (1 +- base_spread)
    """

    OTC_MARKET, OTC_PROVIDER, TAKER, MAKER, USER, MANUAL = 'otc-m', 'otc-p', 'taker', 'maker', 'user', 'manual'

    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey('market.PairSymbol', on_delete=models.PROTECT)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    side = models.CharField(max_length=8, choices=BaseTrade.SIDE_CHOICES)
    amount = get_amount_field()
    price = get_amount_field()
    group_id = get_group_id_field()
    source = models.CharField(max_length=8, choices=(
        (OTC_MARKET, OTC_MARKET), (OTC_PROVIDER, OTC_PROVIDER), (MAKER, MAKER), (TAKER, TAKER), (USER, USER),
        (MANUAL, MANUAL)
    ))
    fee_revenue = get_amount_field()
    value = get_amount_field()

    coin_price = get_amount_field()
    base_price = get_amount_field()
    coin_spread = get_amount_field()
    base_spread = get_amount_field()

    coin_filled_price = get_amount_field(null=True)
    filled_amount = get_amount_field(null=True)
    hedge_key = models.CharField(max_length=16, db_index=True, blank=True)

    fiat_hedge_usdt = get_amount_field(validators=(), default=0)
    fiat_hedge_base = get_amount_field(validators=(), default=0)

    @classmethod
    def new(cls, user_trade: BaseTrade, group_id, source: str, hedge_key: str = None):
        trade_volume = user_trade.amount * user_trade.price
        trade_value = trade_volume * user_trade.base_usdt_price

        other_side = get_other_side(user_trade.side)
        symbol = user_trade.symbol

        coin_raw_price = get_external_price(
            coin=symbol.asset.symbol,
            base_coin=Asset.USDT,
            side=other_side,
            allow_stale=True,
        )
        coin_spread = get_asset_spread(
            coin=symbol.asset.symbol,
            side=other_side,
            value=trade_value
        )

        if symbol.base_asset.symbol == Asset.IRT:
            base_price = get_external_price(
                coin=Asset.USDT,
                base_coin=Asset.IRT,
                side=other_side,
                allow_stale=True,
            )
            base_spread = get_market_spread(
                base_coin=Asset.IRT,
                side=other_side,
                value=trade_value,
            )
        else:
            base_price = 1
            base_spread = 0

        revenue = TradeRevenue(
            created=user_trade.created,
            account=user_trade.account,
            symbol=user_trade.symbol,
            side=user_trade.side,
            amount=user_trade.amount,
            price=user_trade.price,
            group_id=group_id,
            value=trade_value,
            fee_revenue=user_trade.fee_revenue,

            source=source,
            hedge_key=hedge_key,

            coin_spread=coin_spread,
            coin_price=coin_raw_price * spread_to_multiplier(coin_spread, other_side),
            base_price=base_price,
            base_spread=base_spread,
        )

        if source not in (TradeRevenue.OTC_MARKET, TradeRevenue.USER) \
                and user_trade.symbol.base_asset.symbol == Asset.IRT:

            revenue.fiat_hedge_base = trade_volume
            revenue.fiat_hedge_usdt = revenue.coin_price * revenue.amount

            if revenue.side == BUY:
                revenue.fiat_hedge_usdt *= -1
            else:
                revenue.fiat_hedge_base *= -1

        return revenue
