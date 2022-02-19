from decimal import Decimal
from math import log10

from django.db import models, transaction
from django.db.models import Sum

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_trading_price_usdt, SELL
from provider.exchanges import BinanceFuturesHandler, BinanceSpotHandler


class ProviderOrder(models.Model):
    BINANCE = 'binance'

    SPOT, MARGIN, FUTURE = 'spot', 'mar', 'fut'

    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    TRADE, BORROW, LIQUIDATION, WITHDRAW = 'trade', 'borrow', 'liquid', 'withdraw'
    SCOPE_CHOICES = ((TRADE, 'trade'), (BORROW, 'borrow'), (LIQUIDATION, 'liquidation'), (WITHDRAW, 'withdraw'))

    created = models.DateTimeField(auto_now_add=True)

    exchange = models.CharField(max_length=8, default=BINANCE)
    market = models.CharField(max_length=4, default=FUTURE)

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    amount = get_amount_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)

    order_id = models.CharField(
        max_length=64,
        blank=True
    )

    scope = models.CharField(
        max_length=8,
        choices=SCOPE_CHOICES,
    )

    # caller_id = models.PositiveIntegerField(null=True, blank=True)

    @classmethod
    def new_order(cls, asset: Asset, side: str, amount: Decimal, scope: str, market: str = FUTURE) -> 'ProviderOrder':
        with transaction.atomic():
            order = ProviderOrder.objects.create(
                asset=asset, amount=amount, side=side, scope=scope
            )

            symbol = cls.get_trading_symbol(asset)

            if market == cls.FUTURE and asset.symbol == 'SHIB':
                symbol = symbol.replace('SHIB', '1000SHIB')
                amount = round(amount / 1000)

            if market == cls.FUTURE:
                resp = BinanceFuturesHandler.place_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    client_order_id=order.id
                )
            elif market == cls.SPOT:
                resp = BinanceSpotHandler.place_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    client_order_id=order.id
                )
            else:
                raise NotImplementedError

            order.order_id = resp['orderId']
            order.save()

            return order

    @classmethod
    def get_hedge(cls, asset: Asset):
        """
        how much assets we have more!
        :param asset:
        :return:
        """

        system_wallet = asset.get_wallet(Account.system())
        system_balance = system_wallet.get_ledger_balance()

        orders = ProviderOrder.objects.filter(asset=asset).values('side').annotate(amount=Sum('amount'))

        orders_amount = 0

        for order in orders:
            amount = order.get('amount')

            if order.get('side') == cls.SELL:
                amount = -amount

            orders_amount += amount

        return system_balance + orders_amount

    @classmethod
    def get_trading_symbol(cls, asset: Asset) -> str:
        return asset.symbol + 'USDT'

    @classmethod
    def try_hedge_for_new_order(cls, asset: Asset, side: str, amount: Decimal, scope: str) -> bool:
        # todo: this method should not called more than once at a single time

        to_buy = amount if side == cls.BUY else -amount
        hedge_amount = cls.get_hedge(asset) - to_buy

        symbol = cls.get_trading_symbol(asset)

        step_size = BinanceFuturesHandler.get_step_size(symbol)

        if abs(hedge_amount) > step_size / 2:
            side = cls.SELL

            if hedge_amount < 0:
                hedge_amount = -hedge_amount
                side = cls.BUY

            round_digits = -int(log10(step_size))

            order_amount = round(hedge_amount, round_digits)

            # check notional
            price = get_trading_price_usdt(asset.symbol, side=SELL, raw_price=True)

            if order_amount * price < 10:
                return True

            order = cls.new_order(asset, side, order_amount, scope)

            return bool(order)

        return True

