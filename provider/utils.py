import math


def floor_precision(amount: float, precision: int = 0):
    n = pow(10, precision)
    return math.floor(amount * n) / n

