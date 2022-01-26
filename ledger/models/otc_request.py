from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Account
from ledger.models import Asset, Order
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_other_side
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
    EXPIRE_TIME = 30

    created = models.DateTimeField(auto_now_add=True)
    token = models.UUIDField(default=secure_uuid4, db_index=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    from_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='from_otc_requests')
    to_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='to_otc_requests')

    to_amount = get_amount_field()
    from_amount = get_amount_field()
    to_price = get_amount_field()

    def get_trade_config(self) -> TradeConfig:
        if self.from_asset.symbol == Asset.IRT:
            return TradeConfig(
                side=Order.BUY,
                cash=self.from_asset,
                coin=self.to_asset,
                cash_amount=self.from_amount,
                coin_amount=self.to_amount,
            )

        elif self.to_asset.symbol == Asset.IRT:
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
        trading_price = get_trading_price_irt(conf.coin.symbol, other_side)

        if conf.side == 'sell':
            return 1 / trading_price

        return trading_price

    def set_amounts(self, from_amount: Decimal = None, to_amount: Decimal = None):
        assert (from_amount or to_amount) and (not from_amount or not to_amount), 'exactly one amount should presents'

        to_price = self.get_to_price()

        if to_amount:
            from_amount = to_price * to_amount

            if self.to_asset.is_coin():
                self.to_asset.is_trade_amount_valid(to_amount, raise_exception=True)
            else:
                from_amount = from_amount - (from_amount % self.from_asset.trade_quantity_step)  # step coin
                to_amount = from_amount / to_price  # re calc cash

        else:
            to_amount = from_amount / to_price

            if self.to_asset.is_coin():
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