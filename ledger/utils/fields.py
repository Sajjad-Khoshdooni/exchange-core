COMMISSION_MAX_DIGITS = 25

AMOUNT_DECIMAL_PLACES = 18
AMOUNT_MAX_DIGITS = 30


def get_amount_field(max_digits: int = None):
    from django.db import models

    return models.DecimalField(
        max_digits=max_digits or AMOUNT_MAX_DIGITS,
        decimal_places=AMOUNT_DECIMAL_PLACES,
    )
