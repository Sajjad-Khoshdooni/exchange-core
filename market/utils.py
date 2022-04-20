from decimal import Decimal
from typing import Union

from django.db import transaction

from accounts.models import Account
from ledger.models import Wallet, Asset
from market.models import Order, CancelRequest, PairSymbol


def cancel_order(order: Order) -> CancelRequest:
    with transaction.atomic():
        request = CancelRequest.objects.create(order=order)
        Order.cancel_orders(order.symbol, to_cancel_orders=Order.objects.filter(id=order.id))

        return request


def cancel_orders(orders):
    if not orders:
        return
    with transaction.atomic():
        Order.cancel_orders(orders[0].symbol, to_cancel_orders=orders)
        for order in orders:
            CancelRequest.objects.create(order=order)


def get_open_orders(wallet: Wallet):
    return Order.open_objects.filter(
        wallet=wallet,
    )


class MinTradeError(Exception):
    pass


class MaxTradeError(Exception):
    pass


class MinNotionalError(Exception):
    pass


def new_order(symbol: PairSymbol, account: Account, amount: Decimal, price: Decimal, side: str,
              raise_exception: bool = True) -> Union[Order, None]:

    wallet = symbol.asset.get_wallet(account)

    if amount < symbol.min_trade_quantity:
        if raise_exception:
            raise MinTradeError
        else:
            return

    if amount > symbol.max_trade_quantity:
        if raise_exception:
            raise MinTradeError
        else:
            return

    base_asset_symbol = symbol.base_asset.symbol

    if base_asset_symbol == Asset.IRT:
        min_notional = Order.MIN_IRT_ORDER_SIZE
    elif base_asset_symbol == Asset.USDT:
        min_notional = Order.MIN_USDT_ORDER_SIZE
    else:
        raise NotImplementedError

    if amount * price < min_notional:
        if raise_exception:
            raise MinNotionalError
        else:
            return

    with transaction.atomic():
        order = Order.objects.create(
            wallet=wallet,
            symbol=symbol,
            amount=amount,
            price=price,
            side=side,
            fill_type=Order.LIMIT
        )

        order.submit()

    return order
