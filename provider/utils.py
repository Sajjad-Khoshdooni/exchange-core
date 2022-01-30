import math
from decimal import Decimal


def floor_precision(amount: float, precision: int = 0):
    n = pow(10, precision)
    return math.floor(amount * n) / n


def round_with_step_size(amount: Decimal, step_size: Decimal) -> Decimal:
    round_digits = -int(math.log10(step_size))
    return round(amount, round_digits)
