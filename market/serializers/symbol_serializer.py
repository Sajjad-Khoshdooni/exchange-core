import logging

from datetime import timedelta
from django.db.models import Max, Min, Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from accounts.models import Account
from ledger.utils.precision import get_presentation_amount, floor_precision
from market.models import PairSymbol, FillOrder


logger = logging.getLogger(__name__)


class SymbolSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source='asset.symbol', read_only=True)
    base_asset = serializers.CharField(source='base_asset.symbol', read_only=True)
    bookmark = serializers.SerializerMethodField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in ('taker_fee', 'maker_fee', 'min_trade_quantity', 'max_trade_quantity'):
            representation[field] = get_presentation_amount(representation[field])
        return representation

    def get_bookmark(self, pair_symbol: PairSymbol):
        return pair_symbol in self.context.get('bookmarks')

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'taker_fee', 'maker_fee', 'tick_size', 'step_size',
                  'min_trade_quantity', 'max_trade_quantity', 'enable', 'bookmark',)


class SymbolBreifStatsSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source='asset.symbol', read_only=True)
    base_asset = serializers.CharField(source='base_asset.symbol', read_only=True)
    price = serializers.SerializerMethodField()
    change_percent = serializers.SerializerMethodField()
    bookmark = serializers.SerializerMethodField()

    def get_price(self, symbol: PairSymbol):
        last_trade = FillOrder.get_last(symbol=symbol)
        if last_trade:
            return last_trade.format_values()['price']

    def get_bookmark(self, pair_symbol: PairSymbol):
        return pair_symbol in self.context.get('bookmarks')

    @staticmethod
    def get_change_value_pairs(symbol: PairSymbol):
        previous_trade = FillOrder.get_last(symbol=symbol, max_datetime=timezone.now() - timedelta(hours=24))
        if not previous_trade:
            return None, None
        last_trade = FillOrder.get_last(symbol=symbol)
        if not last_trade:
            return None, None
        return last_trade.price, previous_trade.price

    def get_change_percent(self, symbol: PairSymbol):
        last_price, previous_price = self.get_change_value_pairs(symbol)
        if not (last_price and previous_price):
            return
        change_percent = 100 * (last_price - previous_price) / previous_price
        return str(floor_precision(change_percent, 2))
    
    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'enable', 'price', 'change_percent', 'bookmark')


class SymbolStatsSerializer(SymbolBreifStatsSerializer):
    change = serializers.SerializerMethodField()
    high = serializers.SerializerMethodField()
    low = serializers.SerializerMethodField()
    volume = serializers.SerializerMethodField()
    base_volume = serializers.SerializerMethodField()

    def get_change(self, symbol: PairSymbol):
        last_price, previous_price = self.get_change_value_pairs(symbol)
        if not (last_price and previous_price):
            return
        return str(floor_precision((last_price - previous_price), symbol.tick_size))

    def get_high(self, symbol: PairSymbol):
        high_price = FillOrder.objects.filter(
            symbol=symbol,
            created__gt=timezone.now() - timedelta(hours=24),
            created__lte=timezone.now(),
        ).aggregate(max_price=Max('price'))['max_price']
        if high_price:
            return str(floor_precision(high_price, symbol.tick_size))

    def get_low(self, symbol: PairSymbol):
        low_price = FillOrder.objects.filter(
            symbol=symbol,
            created__gt=timezone.now() - timedelta(hours=24),
            created__lte=timezone.now(),
        ).aggregate(min_price=Min('price'))['min_price']
        if low_price:
            return str(floor_precision(low_price, symbol.tick_size))

    def get_volume(self, symbol: PairSymbol):
        total_amount = FillOrder.objects.filter(
            symbol=symbol,
            created__gt=timezone.now() - timedelta(hours=24),
            created__lte=timezone.now(),
        ).aggregate(total_amount=Sum('amount'))['total_amount']
        if total_amount:
            return str(floor_precision(total_amount, symbol.step_size))

    def get_base_volume(self, symbol: PairSymbol):
        total_amount = FillOrder.objects.filter(
            symbol=symbol,
            created__gt=timezone.now() - timedelta(hours=24),
            created__lte=timezone.now(),
        ).aggregate(total_amount=Sum('base_amount'))['total_amount']
        if total_amount:
            return str(floor_precision(total_amount))

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'enable', 'price', 'change', 'change_percent',
                  'high', 'low', 'volume', 'base_volume')


class BookMarkPairSymbolSerializer(serializers.ModelSerializer):
    pair_symbol = serializers.CharField()
    action = serializers.CharField()

    def update(self, instance, validated_data):
        pair_symbol = get_object_or_404(PairSymbol, name=validated_data.get('pair_symbol'))
        action = validated_data['action']
        if action == 'add':
            instance.account.bookmark_market.add(pair_symbol)
        elif action == 'remove':
            instance.account.bookmark_market.remove(pair_symbol)
        instance.save()
        return instance

    class Meta:
        model = Account
        fields = ['pair_symbol', 'action', ]
