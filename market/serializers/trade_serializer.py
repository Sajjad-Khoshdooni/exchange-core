from decimal import Decimal

from rest_framework import serializers

from ledger.models import Asset
from ledger.utils.precision import floor_precision
from market.models import FillOrder, Order


class FillOrderSerializer(serializers.ModelSerializer):
    coin = serializers.CharField(source='symbol.asset.symbol')
    pair = serializers.CharField(source='symbol.base_asset.symbol')
    pair_amount = serializers.CharField(source='base_amount')
    side = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()

    def get_side(self, instance: FillOrder):
        return instance.get_side(self.context['account'], self.context['index'])

    def get_fee_amount(self, instance: FillOrder):
        return instance.get_fee(self.context['account'], self.context['index'])

    def to_representation(self, trade: FillOrder):
        data = super(FillOrderSerializer, self).to_representation(trade)
        amount = floor_precision(Decimal(data['amount']), trade.symbol.step_size)
        if not amount:
            amount = floor_precision(trade.symbol.min_trade_quantity, trade.symbol.step_size)
        data['amount'] = str(amount)
        data['price'] = str(floor_precision(Decimal(data['price']), trade.symbol.tick_size))
        data['pair_amount'] = str(floor_precision(Decimal(data['pair_amount']), trade.symbol.tick_size))
        if 'fee_amount' in data:
            if data['side'] == Order.BUY:
                data['fee_amount'] = trade.symbol.asset.get_presentation_amount(data['fee_amount'])
            elif trade.symbol.base_asset.symbol == Asset.IRT:
                data['fee_amount'] = trade.symbol.asset.get_presentation_price_irt(data['fee_amount'])
            elif trade.symbol.base_asset.symbol == Asset.USDT:
                data['fee_amount'] = trade.symbol.asset.get_presentation_price_usdt(data['fee_amount'])
            data['fee_asset'] = data['coin'] if data['side'] == Order.BUY else data['pair']
        return data

    class Meta:
        model = FillOrder
        fields = ('created', 'coin', 'pair', 'side', 'amount', 'price', 'pair_amount', 'fee_amount',)


class TradeSerializer(FillOrderSerializer):
    coin = serializers.CharField(source='symbol.asset.symbol')
    pair = serializers.CharField(source='symbol.base_asset.symbol')
    pair_amount = serializers.CharField(source='base_amount')

    class Meta:
        model = FillOrder
        fields = ('created', 'coin', 'pair', 'amount', 'price', 'pair_amount', 'is_buyer_maker')