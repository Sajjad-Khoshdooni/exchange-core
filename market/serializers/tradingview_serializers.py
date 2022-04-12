from decimal import Decimal

from rest_framework import serializers

from ledger.utils.precision import floor_precision
from market.models import PairSymbol


class OHLCVSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField(source='timestamp')
    open = serializers.SerializerMethodField()
    high = serializers.SerializerMethodField()
    low = serializers.SerializerMethodField()
    close = serializers.SerializerMethodField()
    volume = serializers.SerializerMethodField()

    def get_open(self, obj):
        return self.format_price(self.context['symbol'], obj['open'])

    def get_high(self, obj):
        return self.format_price(self.context['symbol'], obj['high'])

    def get_low(self, obj):
        return self.format_price(self.context['symbol'], obj['low'])

    def get_close(self, obj):
        return self.format_price(self.context['symbol'], obj['close'])

    def get_volume(self, obj):
        return floor_precision(obj['volume'], self.context['symbol'].step_size)

    @staticmethod
    def format_price(symbol: PairSymbol, price: Decimal):
        return floor_precision(price, symbol.tick_size)
