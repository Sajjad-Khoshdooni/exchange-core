import logging
from dataclasses import dataclass
from decimal import Decimal

from ledger.models import Asset
from ledger.utils.cache import cache_for
from ledger.utils.external_price import BUY, SELL

logger = logging.getLogger(__name__)


@dataclass
class TradingPair:
    side: str
    coin: Asset
    base: Asset
    coin_amount: Decimal
    base_amount: Decimal


def get_trading_pair(from_asset: Asset, to_asset: Asset, from_amount: Decimal = None, to_amount: Decimal = None) -> TradingPair:

    if from_asset.symbol in (Asset.IRT, Asset.USDT) and to_asset.symbol != Asset.IRT:
        return TradingPair(
            side=BUY,
            coin=to_asset,
            base=from_asset,
            coin_amount=to_amount,
            base_amount=from_amount,
        )

    elif to_asset.symbol in (Asset.IRT, Asset.USDT):
        return TradingPair(
            side=SELL,
            coin=from_asset,
            base=to_asset,
            coin_amount=from_amount,
            base_amount=to_amount,
        )

    else:
        raise NotImplementedError


@cache_for(300)
def get_otc_spread(coin: str, side: str, value: Decimal = None, base_coin: str = None) -> Decimal:
    from ledger.models import CategorySpread, Asset, MarketSpread

    asset = Asset.get(coin)
    step = CategorySpread.get_step(value)

    category = asset.spread_category

    asset_spread = CategorySpread.objects.filter(category=category, step=step, side=side).first()

    if not asset_spread:
        logger.warning("No category spread defined for %s step = %s, side = %s" % (category, step, side))
        asset_spread = CategorySpread()

    spread = asset_spread.spread

    if base_coin == Asset.IRT:
        market_spread = MarketSpread.objects.filter(step=step, side=side).first()

        if market_spread:
            spread += market_spread.spread

    return spread / 100


def spread_to_multiplier(spread: Decimal, side: str):
    if side == BUY:
        return 1 - spread
    else:
        return 1 + spread
