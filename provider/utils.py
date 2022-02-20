import math
from decimal import Decimal


def round_with_step_size(amount: Decimal, step_size: Decimal) -> Decimal:
    round_digits = -int(math.log10(step_size))
    return round(amount, round_digits)
