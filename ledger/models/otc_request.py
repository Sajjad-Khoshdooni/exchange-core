from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Account
from ledger.exceptions import SmallAmountTrade
from ledger.models import Asset, Order, Wallet
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_other_side, get_trading_price_irt, BUY, get_trading_price_usdt
from ledger.utils.random import secure_uuid4
from dataclasses import dataclass


@dataclass
class TradeConfig:
    side: str
    coin: Asset
    cash: Asset
    coin_amount: Decimal
    cash_amount: Decimal


class OTCRequest(models.Model):
    EXPIRE_TIME = 6

    created = models.DateTimeField(auto_now_add=True)
    token = models.UUIDField(default=secure_uuid4, db_index=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    from_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='from_otc_requests')
    to_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='to_otc_requests')

    to_amount = get_amount_field()
    from_amount = get_amount_field()
    to_price = get_amount_field()

    market = models.CharField(
        max_length=8,
        default=Wallet.SPOT,
        choices=((Wallet.SPOT, Wallet.SPOT), (Wallet.MARGIN, Wallet.MARGIN)),
    )

    @classmethod
    def new_trade(cls, account: Account, market: str, from_asset: Asset, to_asset: Asset, from_amount: Decimal = None,
                  to_amount: Decimal = None, allow_small_trades: bool = False) -> 'OTCRequest':

        assert from_amount or to_amount

        otc_request = OTCRequest(
            account=account,
            from_asset=from_asset,
            to_asset=to_asset,
            market=market,
        )

        otc_request.set_amounts(from_amount, to_amount)

        if not allow_small_trades:
            if from_amount:
                check_asset, check_amount = from_asset, from_amount
            else:
                check_asset, check_amount = to_asset, to_amount

            if check_amount * get_trading_price_irt(check_asset.symbol, BUY, raw_price=True) < 98_000:
                raise SmallAmountTrade()

        from_wallet = from_asset.get_wallet(account, otc_request.market)
        from_wallet.has_balance(otc_request.from_amount, raise_exception=True)

        otc_request.save()

        return otc_request

    def get_trade_config(self) -> TradeConfig:
        from_symbol = self.from_asset.symbol
        to_symbol = self.to_asset.symbol

        if from_symbol in (Asset.IRT, Asset.USDT) and to_symbol != Asset.IRT:
            return TradeConfig(
                side=Order.BUY,
                cash=self.from_asset,
                coin=self.to_asset,
                cash_amount=self.from_amount,
                coin_amount=self.to_amount,
            )

        elif to_symbol in (Asset.IRT, Asset.USDT):
            return TradeConfig(
                side=Order.SELL,
                cash=self.to_asset,
                coin=self.from_asset,
                cash_amount=self.to_amount,
                coin_amount=self.from_amount,
            )

        else:
            raise NotImplementedError

    def get_to_price(self):
        from ledger.utils.price import get_trading_price_irt

        conf = self.get_trade_config()
        other_side = get_other_side(conf.side)

        if conf.cash.symbol == Asset.IRT:
            trading_price = get_trading_price_irt(conf.coin.symbol, other_side)
        elif conf.cash.symbol == Asset.USDT:
            trading_price = get_trading_price_usdt(conf.coin.symbol, other_side)
        else:
            raise NotImplementedError

        if conf.side == 'sell':
            return 1 / trading_price

        return trading_price

    def set_amounts(self, from_amount: Decimal = None, to_amount: Decimal = None):
        assert (from_amount or to_amount) and (not from_amount or not to_amount), 'exactly one amount should presents'

        to_price = self.get_to_price()

        if to_amount:
            from_amount = to_price * to_amount

            if self.from_asset.is_trade_base() and self.to_asset.symbol != Asset.IRT:
                self.to_asset.is_trade_amount_valid(to_amount, raise_exception=True)
            else:
                from_amount = from_amount - (from_amount % self.from_asset.trade_quantity_step)  # step coin
                to_amount = from_amount / to_price  # re calc cash

        else:
            to_amount = from_amount / to_price

            if self.from_asset.is_trade_base() and self.to_asset.symbol != Asset.IRT:
                to_amount = to_amount - (to_amount % self.to_asset.trade_quantity_step)  # step coin
                from_amount = to_amount * to_price  # re calc cash
            else:
                self.from_asset.is_trade_amount_valid(from_amount, raise_exception=True)

        self.to_price = to_price
        self.from_amount = from_amount
        self.to_amount = to_amount

    def get_expire_time(self) -> datetime:
        return self.created + timedelta(seconds=OTCRequest.EXPIRE_TIME)

    def expired(self):
        return (timezone.now() - self.created).total_seconds() >= self.EXPIRE_TIME

    def __str__(self):
        return 'Buy %s %s from %s' % (self.to_asset.get_presentation_amount(self.to_amount), self.to_asset, self.from_asset,)