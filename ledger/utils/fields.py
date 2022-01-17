COMMISSION_MAX_DIGITS = 25

AMOUNT_DECIMAL_PLACES = 18
AMOUNT_MAX_DIGITS = 40


def get_amount_field(max_digits: int = None, decimal_places: int = None):
    from django.db import models

    return models.DecimalField(
        max_digits=max_digits or AMOUNT_MAX_DIGITS,
        decimal_places=decimal_places or AMOUNT_DECIMAL_PLACES,
    )


def get_serializer_amount_field(max_digits: int = None, decimal_places: int = None, **kwargs):
    from rest_framework import serializers

    return serializers.DecimalField(
        max_digits=max_digits or AMOUNT_MAX_DIGITS,
        decimal_places=decimal_places or AMOUNT_DECIMAL_PLACES,
        **kwargs
    )
