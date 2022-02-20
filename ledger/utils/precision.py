from decimal import Decimal, ROUND_DOWN


def floor_precision(amount: Decimal, precision: int = 0):
    step = precision_to_step(precision)
    return amount.quantize(step, rounding=ROUND_DOWN)


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


def precision_to_step(precision: int) -> Decimal:
    precision = int(precision)

    if precision <= 0:
        return Decimal('1' + '0' * -precision)
    else:
        return Decimal('0.' + '0' * (precision - 1) + '1')


def get_presentation_amount(amount: Decimal, precision: int) -> str:
    if not isinstance(amount, Decimal):
        amount = Decimal(amount)

    rounded = format(floor_precision(amount, precision), 'f')

    if '.' not in rounded:
        return rounded
    else:
        return rounded.rstrip('0').rstrip('.') or '0'


def humanize_number(num):
    return '{:,}'.format(num)
