from django.db import models

from ledger.models import Asset
from ledger.utils.external_price import BUY, get_external_price, get_other_side, SELL
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
    value_irt = get_amount_field(default=0)

    coin_price = get_amount_field()
    coin_spread = get_amount_field()

    base_spread = get_amount_field()

    coin_filled_price = get_amount_field(null=True)
    filled_amount = get_amount_field(null=True)
    gap_revenue = get_amount_field(validators=(), null=True)
    hedge_key = models.CharField(max_length=16, db_index=True, blank=True)

    base_usdt_price = get_amount_field(decimal_places=20)

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

        coin_price = coin_raw_price * spread_to_multiplier(coin_spread, other_side)

        if symbol.base_asset.symbol == Asset.IRT:
            base_spread = get_market_spread(
                base_coin=Asset.IRT,
                side=other_side,
                value=trade_value,
            )
        else:
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
            value_irt=trade_volume * user_trade.base_irt_price,
            fee_revenue=user_trade.fee_revenue,

            source=source,
            hedge_key=hedge_key,

            coin_spread=coin_spread,
            coin_price=coin_price,

            base_spread=base_spread,
            base_usdt_price=user_trade.base_usdt_price,
        )

        return revenue

    def get_gap_revenue(self):
        gap = self.amount * (self.coin_price - self.coin_filled_price)

        if self.side == SELL:
            gap = -gap

        return gap
