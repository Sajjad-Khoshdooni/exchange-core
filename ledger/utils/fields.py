from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models
from rest_framework import serializers
from decimal import Decimal

from django.db.models import CharField


PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

COMMISSION_MAX_DIGITS = 25

AMOUNT_DECIMAL_PLACES = 18
AMOUNT_MAX_DIGITS = 40


def get_amount_field(max_digits: int = None, decimal_places: int = None, default: Decimal = None):

    kwargs = {
        'max_digits': max_digits or AMOUNT_MAX_DIGITS,
        'decimal_places': decimal_places or AMOUNT_DECIMAL_PLACES,
        'validators': [MinValueValidator(0)]
    }

    if default is not None:
        kwargs['default'] = default

    return models.DecimalField(**kwargs)


def get_serializer_amount_field(max_digits: int = None, decimal_places: int = None, **kwargs):

    return serializers.DecimalField(
        max_digits=max_digits or AMOUNT_MAX_DIGITS,
        decimal_places=decimal_places or AMOUNT_DECIMAL_PLACES,
        **kwargs
    )


def get_status_field():

    return models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)]
    )


def get_lock_field(null: bool = False):
    return models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE, null=null, blank=null)


def get_group_id_field():
    return models.UUIDField(default=uuid4)


def get_address_field():
    return CharField(max_length=256)
