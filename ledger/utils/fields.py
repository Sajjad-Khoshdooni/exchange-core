from decimal import Decimal
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CharField
from rest_framework import serializers


from ledger.utils.cache import cache_for
from ledger.utils.precision import normalize_fraction


PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'


def get_amount_field(default: Decimal = None, max_digits: int = None, decimal_places: int = None, null: bool = False):

    kwargs = {
        'max_digits': max_digits or 30,
        'decimal_places': decimal_places or 8,
        'validators': [MinValueValidator(0)],
        'blank': null,
        'null': null,
    }

    if default is not None:
        kwargs['default'] = default

    return models.DecimalField(**kwargs)


def get_serializer_amount_field(**kwargs):

    return SerializerDecimalField(
        max_digits=30,
        decimal_places=8,
        min_value=0,
        **kwargs,
    )


def get_status_field():

    return models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, 'در انتظار تایید'), (CANCELED, 'لغو شده'), (DONE, 'انجام شده')]
    )


def get_group_id_field(db_index: bool = False, null: bool = False):
    return models.UUIDField(default=uuid4, editable=False, db_index=db_index, null=null, blank=null)


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


@cache_for(time=600)
def get_irt_market_assets():
    from market.models import PairSymbol
    from ledger.models import Asset
    return set(PairSymbol.objects.select_related('base_asset').filter(
        enable=True,
        base_asset__symbol=Asset.IRT
    ).values_list('asset', flat=True))
