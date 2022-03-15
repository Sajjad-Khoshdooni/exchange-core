import logging

from rest_framework import serializers

from ledger.utils.precision import get_presentation_amount
from market.models import PairSymbol

logger = logging.getLogger(__name__)


class SymbolSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source='asset.symbol', read_only=True)
    base_asset = serializers.CharField(source='base_asset.symbol', read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in ('taker_fee', 'maker_fee', 'min_trade_quantity', 'max_trade_quantity'):
            representation[field] = get_presentation_amount(representation[field])
        return representation

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'taker_fee', 'maker_fee', 'tick_size', 'step_size',
                  'min_trade_quantity', 'max_trade_quantity', 'enable',)
