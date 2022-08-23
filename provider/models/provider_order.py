import logging
import math
from decimal import Decimal
from math import log10

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum, CheckConstraint, Q

from accounts.models import Account
from ledger.exceptions import HedgeError
from ledger.models import Asset, Wallet
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import floor_precision
from ledger.utils.price import get_trading_price_usdt, SELL, BUY
from provider.exchanges import BinanceSpotHandler, BinanceFuturesHandler
from provider.exchanges.interface.kucoin_interface import KucoinFuturesHandler, KucoinSpotHandler

logger = logging.getLogger(__name__)


class ProviderOrder(models.Model):

    SPOT, MARGIN, FUTURE = 'spot', 'mar', 'fut'

    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    TRADE, BORROW, LIQUIDATION, WITHDRAW, HEDGE, PROVIDE_BASE, FAKE = \
        'trade', 'borrow', 'liquid', 'withdraw', 'hedge', 'prv-base', 'fake'

    SCOPE_CHOICES = ((TRADE, 'trade'), (BORROW, 'borrow'), (LIQUIDATION, 'liquidation'), (WITHDRAW, 'withdraw'),
                     (HEDGE, HEDGE), (PROVIDE_BASE, PROVIDE_BASE), (FAKE, FAKE))

    created = models.DateTimeField(auto_now_add=True)

    exchange = models.CharField(max_length=32)
    market = models.CharField(
        max_length=4,
        default=FUTURE,
        choices=((SPOT, 'spot'), (FUTURE, 'future'), (MARGIN, 'margin'))
    )

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

    hedge_amount = get_amount_field(default=Decimal(0))

    # caller_id = models.PositiveIntegerField(null=True, blank=True)

    @classmethod
    def new_order(cls, asset: Asset, side: str, amount: Decimal, scope: str, market: str = FUTURE,
                  hedge_amount: Decimal = 0) -> 'ProviderOrder':

        handler = asset.get_hedger()
        with transaction.atomic():
            order = ProviderOrder.objects.create(
                asset=asset,
                amount=amount,
                side=side,
                scope=scope,
                market=market,
                hedge_amount=hedge_amount,
                exchange=asset.hedge_method
            )

            symbol = handler.get_trading_symbol(asset.symbol)

            if asset.get_hedger().NAME == BinanceFuturesHandler.NAME and market == cls.FUTURE and asset.symbol == 'SHIB':
                symbol = symbol.replace('SHIB', '1000SHIB')
                amount = round(amount / 1000)

            if market == cls.FUTURE:
                if asset.get_hedger().NAME == KucoinSpotHandler.NAME:
                    handler = KucoinFuturesHandler
                else:
                    handler = BinanceFuturesHandler

            elif market == cls.SPOT:
                if asset.get_hedger().NAME == KucoinSpotHandler.NAME:
                    handler = KucoinSpotHandler
                else:
                    handler = BinanceSpotHandler

            else:
                raise NotImplementedError

            resp = handler().place_order(
                symbol=symbol,
                side=side,
                amount=amount,
                client_order_id=order.id
            )

            order.order_id = resp['orderId']
            order.save()

            return order

    @classmethod
    def get_hedge(cls, asset: Asset):
        """
        how much assets we have more!

        out = -internal - binance transfer deposit
        hedge = all assets - users = (internal + binance manual deposit + binance transfer deposit + binance trades)
                + system + out = system + binance trades + binance manual deposit

        given binance manual deposit = 0 -> hedge = system + binance manual deposit + binance trades
        """

        system_balance = Wallet.objects.filter(
            account__type=Account.SYSTEM,
            asset=asset
        ).aggregate(
            sum=Sum('balance')
        )['sum'] or 0

        orders = ProviderOrder.objects.filter(asset=asset).values('side').annotate(amount=Sum('amount'))

        orders_amount = 0

        for order in orders:
            amount = order.get('amount')

            if order.get('side') == cls.SELL:
                amount = -amount

            orders_amount += amount

        return system_balance + orders_amount

    @classmethod
    def try_hedge_for_new_order(cls, asset: Asset, scope: str, amount: Decimal = 0, side: str = '',
                                dry_run: bool = False, raise_exception: bool = False) -> bool:
        # todo: this method should not called more than once at a single time
        handler = asset.get_hedger()
        if settings.DEBUG_OR_TESTING:
            logger.info('ignored due to debug')
            return True

        if not asset.hedge_method:
            logger.info('ignored due to no hedge method')
            return True

        to_buy = amount if side == cls.BUY else -amount
        hedge_amount = cls.get_hedge(asset) - to_buy

        symbol = handler.get_trading_symbol(asset.symbol)

        handler = asset.get_hedger()
        market = handler.MARKET_TYPE

        step_size = handler.get_step_size(symbol)

        logger.info('Hedge amount for %s: %s' % (asset, hedge_amount))

        # Hedge strategy: don't sell assets ASAP and hold them!

        if hedge_amount < 0:
            threshold = step_size / 2
        else:
            threshold = step_size * 2

        if abs(hedge_amount) > threshold:
            side = cls.SELL

            if hedge_amount < 0:
                hedge_amount = -hedge_amount
                side = cls.BUY

            round_digits = -int(log10(step_size))

            order_amount = round(hedge_amount, round_digits)

            # check notional
            price = get_trading_price_usdt(asset.symbol, side=SELL, raw_price=True)

            min_hedge_amount = handler.get_min_notional()

            if order_amount * price < min_hedge_amount:
                logger.info('ignored due to small order')
                return True

            if not dry_run:
                if market == cls.SPOT and side == cls.SELL:
                    balance_map = handler.get_spot_handler().get_free_dict()
                    balance = balance_map[asset.symbol]

                    if balance < order_amount:
                        diff = order_amount - balance

                        if diff * price < 10:
                            order_amount = floor_precision(balance, round_digits)

                            if order_amount * price < 10:
                                logger.info('ignored due to small order')
                                return True

                symbol = handler.get_trading_symbol(asset.symbol)

                if side == BUY and symbol.endswith('BUSD'):
                    balance_map = BinanceSpotHandler().get_free_dict()
                    busd_balance = balance_map['BUSD']

                    needed_busd = order_amount * price

                    if needed_busd > busd_balance:
                        logger.info('providing busd for order')
                        to_buy_busd = max(math.ceil((needed_busd - busd_balance) * Decimal('1.01')), 11)

                        cls.new_order(
                            asset=Asset.get('BUSD'),
                            side=BUY,
                            amount=Decimal(to_buy_busd),
                            scope=ProviderOrder.PROVIDE_BASE,
                            market=ProviderOrder.SPOT,
                            hedge_amount=Decimal(0)
                        )

                order = cls.new_order(asset, side, order_amount, scope, market=market, hedge_amount=hedge_amount)

                if not order and raise_exception:
                    raise HedgeError

                return bool(order)

            else:
                logger.info('New provider order with %s, %s, %s, %s, %s' % (asset, side, order_amount, scope, market))
                if order_amount * price > 20:
                    logger.info('Large value: %s' % (order_amount * price))

                return True

        return True

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_provider_order_amount', ), ]
