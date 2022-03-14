import logging

from rest_framework import serializers

from market.models import PairSymbol

logger = logging.getLogger(__name__)


class SymbolSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source='asset.symbol', read_only=True)
    base_asset = serializers.CharField(source='asset.symbol', read_only=True)

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'taker_fee', 'maker_fee', 'tick_size', 'step_size',
                  'min_trade_quantity', 'max_trade_quantity', 'enable',)
