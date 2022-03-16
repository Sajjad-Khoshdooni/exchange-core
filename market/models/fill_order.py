from decimal import Decimal

from django.db import models

from accounts.models import Account
from ledger.models import Trx
from ledger.utils.fields import get_amount_field, get_group_id_field, get_price_field
from market.models import Order, PairSymbol


class FillOrder(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)

    taker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='taken_fills')
    maker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='made_fills')

    amount = get_amount_field()
    price = get_price_field()
    is_buyer_maker = models.BooleanField()

    group_id = get_group_id_field()

    trade_trx_list = None
    base_amount = get_amount_field()
    taker_fee_amount = get_amount_field()
    maker_fee_amount = get_amount_field()

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
        assert self.trade_trx_list
        self.base_amount = self.trade_trx_list['base'].amount
        self.taker_fee_amount = self.trade_trx_list['taker_fee'].amount if self.trade_trx_list[
            'taker_fee'] else Decimal(0)
        self.maker_fee_amount = self.trade_trx_list['maker_fee'].amount if self.trade_trx_list[
            'maker_fee'] else Decimal(0)
        return super(FillOrder, self).save(**kwargs)

    def __str__(self):
        return f'{self.symbol}-{Order.BUY if self.is_buyer_maker else Order.SELL} ' \
               f'({self.taker_order_id}-{self.maker_order_id}) ' \
               f'[p:{self.price:.2f}] (a:{self.amount:.5f})'

    def init_trade_trxs(self, system: 'Account' = None):
        if not system:
            system = Account.system()

        self.trade_trx_list = {
            'amount': self.__init_trade_trx(),
            'base': self.__init_base_trx(),
            'taker_fee': self.__init_fee_trx(self.taker_order, is_taker=True, system=system),
            'maker_fee': self.__init_fee_trx(self.maker_order, is_taker=False, system=system),
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
