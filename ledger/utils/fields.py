from decimal import Decimal
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CharField
from rest_framework import serializers

from ledger.utils.precision import normalize_fraction

PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

COMMISSION_MAX_DIGITS = 32

AMOUNT_DECIMAL_PLACES = 18
AMOUNT_MAX_DIGITS = 40

PRICE_DECIMAL_PLACES = 18
PRICE_MAX_DIGITS = 40


def get_amount_field(max_digits: int = None, decimal_places: int = None, default: Decimal = None):

    kwargs = {
        'max_digits': max_digits or AMOUNT_MAX_DIGITS,
        'decimal_places': decimal_places or AMOUNT_DECIMAL_PLACES,
        'validators': [MinValueValidator(0)]
    }

    if default is not None:
        kwargs['default'] = default

    return models.DecimalField(**kwargs)


def get_price_field(max_digits: int = None, decimal_places: int = None, default: Decimal = None):

    kwargs = {
        'max_digits': max_digits or PRICE_MAX_DIGITS,
        'decimal_places': decimal_places or PRICE_DECIMAL_PLACES,
        'validators': [MinValueValidator(0)]
    }

    if default is not None:
        kwargs['default'] = default

    return models.DecimalField(**kwargs)


def get_serializer_amount_field(max_digits: int = None, decimal_places: int = None, **kwargs):

    return SerializerDecimalField(
        max_digits=max_digits or AMOUNT_MAX_DIGITS,
        decimal_places=decimal_places or AMOUNT_DECIMAL_PLACES,
        **kwargs
    )


def get_status_field():

    return models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, 'در انتظار تایید'), (CANCELED, 'لغو شده'), (DONE, 'انجام شده')]
    )


def get_lock_field(null: bool = True, **kwargs):
    return models.OneToOneField(
        'ledger.BalanceLock', on_delete=models.SET_NULL, null=null, blank=null, editable=False, **kwargs)


def get_group_id_field(db_index: bool = False):
    return models.UUIDField(default=uuid4, editable=False, db_index=db_index)


def get_address_field():
    return CharField(max_length=256)


def get_created_field():
    return models.DateTimeField(auto_now_add=True)


def get_modified_field():
    return models.DateTimeField(auto_now=True)


class SerializerDecimalField(serializers.DecimalField):
    def to_representation(self, data: Decimal):
        if data is None:
            return None

        if not isinstance(data, Decimal):
            data = Decimal(str(data).strip())

        return str(normalize_fraction(data))
