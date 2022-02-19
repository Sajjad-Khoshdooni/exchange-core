from decimal import Decimal

from provider.utils import floor_precision


def get_precision(amount: Decimal) -> int:
    amount = str(amount)

    if '.' in amount:
        amount = amount.rstrip('0').rstrip('.')

    if '.' not in amount:
        return len(amount.rstrip('0')) - len(amount)
    else:
        return len(amount.split('.')[1])


def decimal_to_str(amount: Decimal):
    amount = str(amount)
    if '.' in amount:
        amount = amount.rstrip('0').rstrip('.')
    return amount


def get_presentation_amount(amount: Decimal, precision: int):
    if isinstance(amount, str):
        amount = Decimal(amount)

    rounded = str(floor_precision(amount, precision))

    if '.' not in rounded:
        return rounded
    else:
        return rounded.rstrip('0').rstrip('.') or '0'
