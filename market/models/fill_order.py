import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from accounts.models import Account
from ledger.models import Trx, OTCTrade
from ledger.utils.fields import get_amount_field, get_group_id_field, get_price_field
from ledger.utils.precision import floor_precision, precision_to_step
from market.models import Order, PairSymbol
from ledger.utils.precision import get_presentation_amount


logger = logging.getLogger(__name__)


class FillOrder(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)

    taker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='taken_fills')
    maker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='made_fills')

    amount = get_amount_field()
    price = get_price_field()
    is_buyer_maker = models.BooleanField()

    group_id = get_group_id_field()

    base_amount = get_amount_field()
    taker_fee_amount = get_amount_field()
    maker_fee_amount = get_amount_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trade_trx_list = None

    def side(self, account: Account, list_index: int):
        buy_order = self.maker_order if self.is_buyer_maker else self.taker_order
        sell_order = self.taker_order if self.is_buyer_maker else self.maker_order
        if buy_order.wallet.account != sell_order.wallet.account:
            if account == buy_order.wallet.account:
                return Order.BUY
            if account == sell_order.wallet.account:
                return Order.SELL
            raise Exception('invalid account')
        else:
            return Order.BUY if list_index % 2 == 0 else Order.SELL

    def fee(self, account: Account, list_index: int):
        if self.is_buyer_maker:
            return self.maker_fee_amount if self.side(account, list_index) == Order.BUY else self.taker_fee_amount
        else:
            return self.maker_fee_amount if self.side(account, list_index) == Order.SELL else self.taker_fee_amount

    def save(self, **kwargs):
        assert self.taker_order.symbol == self.maker_order.symbol == self.symbol
        self.calculate_amounts_from_trx()
        return super(FillOrder, self).save(**kwargs)

    def calculate_amounts_from_trx(self):
        assert self.trade_trx_list
        self.base_amount = self.trade_trx_list['base'].amount
        self.taker_fee_amount = self.trade_trx_list['taker_fee'].amount if self.trade_trx_list[
            'taker_fee'] else Decimal(0)
        self.maker_fee_amount = self.trade_trx_list['maker_fee'].amount if self.trade_trx_list[
            'maker_fee'] else Decimal(0)

    def __str__(self):
        return f'{self.symbol}-{Order.BUY if self.is_buyer_maker else Order.SELL} ' \
               f'({self.taker_order_id}-{self.maker_order_id}) ' \
               f'[p:{self.price:.2f}] (a:{self.amount:.5f})'

    def init_trade_trxs(self, system: 'Account' = None, ignore_fee=False):
        if not system:
            system = Account.system()

        self.trade_trx_list = {
            'amount': self.__init_trade_trx(),
            'base': self.__init_base_trx(),
            'taker_fee': Decimal(0) if ignore_fee else self.__init_fee_trx(self.taker_order, is_taker=True,
                                                                           system=system),
            'maker_fee': Decimal(0) if ignore_fee else self.__init_fee_trx(self.maker_order, is_taker=False,
                                                                           system=system),
        }
        return list(self.trade_trx_list.values())

    def __init_trade_trx(self):
        return Trx(
            sender=self.maker_order.wallet if self.taker_order.side == Order.BUY else self.taker_order.wallet,
            receiver=self.taker_order.wallet if self.taker_order.side == Order.BUY else self.maker_order.wallet,
            amount=self.amount,
            group_id=self.group_id,
            scope=Trx.TRADE
        )

    def __init_base_trx(self):
        return Trx(
            sender=self.maker_order.base_wallet if self.taker_order.side == Order.SELL else self.taker_order.base_wallet,
            receiver=self.taker_order.base_wallet if self.taker_order.side == Order.SELL else self.maker_order.base_wallet,
            amount=self.amount * self.price,
            group_id=self.group_id,
            scope=Trx.TRADE
        )

    def __init_fee_trx(self, order, is_taker, system: 'Account' = None):
        if not system:
            system = Account.system()

        fee = order.symbol.taker_fee if is_taker else order.symbol.maker_fee

        fee_wallet = order.wallet if order.side == Order.BUY else order.base_wallet
        trx_amount = fee * (self.amount if order.side == Order.BUY else self.amount * self.price)

        if trx_amount:
            return Trx(
                sender=fee_wallet,
                receiver=fee_wallet.asset.get_wallet(system, market=fee_wallet.market),
                amount=trx_amount,
                group_id=self.group_id,
                scope=Trx.TRADE
            )
    
    @classmethod
    def get_last(cls, symbol: 'PairSymbol'):
        return cls.objects.filter(symbol=symbol).order_by('-id').first()

    def format_values(self):
        return {
            'amount': str(get_presentation_amount(self.amount, self.symbol.step_size)),
            'price': str(get_presentation_amount(self.price, self.symbol.tick_size)),
            'total': str(get_presentation_amount(self.amount * self.price, self.symbol.tick_size)),
        }

    @classmethod
    def create_for_otc_trade(cls, otc_trade: 'OTCTrade'):
        market_symbol = None
        try:
            config = otc_trade.otc_request.get_trade_config()
            market_symbol = f'{config.coin.symbol}{config.cash.symbol}'.upper()
            symbol = PairSymbol.get_by(name=market_symbol)
            amount = floor_precision(config.coin_amount, symbol.step_size)
            price = (config.cash_amount / config.coin_amount).quantize(
                precision_to_step(symbol.tick_size), rounding=ROUND_HALF_UP)
            system_wallet = symbol.asset.get_wallet(Account.system(), market=otc_trade.otc_request.market)
            maker_order = Order.objects.create(
                wallet=system_wallet,
                symbol=symbol,
                amount=amount,
                price=price,
                side=Order.get_opposite_side(config.side),
                fill_type=Order.MARKET,
                status=Order.FILLED,
            )
            taker_wallet = symbol.asset.get_wallet(otc_trade.otc_request.account, market=otc_trade.otc_request.market)
            taker_order = Order.objects.create(
                wallet=taker_wallet,
                symbol=symbol,
                amount=amount,
                price=price,
                side=config.side,
                fill_type=Order.MARKET,
                status=Order.FILLED,
            )
            fill_order = cls(
                symbol=symbol,
                taker_order=taker_order,
                maker_order=maker_order,
                amount=amount,
                price=price,
                is_buyer_maker=(maker_order.side == Order.BUY),
                group_id=otc_trade.group_id
            )
            fill_order.init_trade_trxs(ignore_fee=True)
            fill_order.save()
            # for key in ('taker_fee', 'maker_fee'):
            #     if fill_order.trade_trx_list[key]:
            #         fill_order.trade_trx_list[key].save()
        except PairSymbol.DoesNotExist:
            logger.exception(f'Could not found market {market_symbol}')
