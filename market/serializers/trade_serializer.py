from decimal import Decimal

from rest_framework import serializers

from ledger.utils.precision import get_presentation_amount
from market.models import FillOrder, Order


class FillOrderSerializer(serializers.ModelSerializer):
    coin = serializers.CharField(source='symbol.asset.symbol')
    pair = serializers.CharField(source='symbol.base_asset.symbol')
    pair_amount = serializers.CharField(source='base_amount')
    side = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()

    def get_side(self, instance: FillOrder):
        return instance.side(self.context['account'], self.context['index'])

    def get_fee_amount(self, instance: FillOrder):
        return instance.fee(self.context['account'], self.context['index'])

    def to_representation(self, trade: FillOrder):
        data = super(FillOrderSerializer, self).to_representation(trade)
        data['amount'] = str(get_presentation_amount(Decimal(data['amount']), trade.symbol.step_size))
        data['pair_amount'] = str(get_presentation_amount(Decimal(data['pair_amount']), trade.symbol.tick_size))
        data['fee_amount'] = str(get_presentation_amount(Decimal(data['fee_amount']), trade.symbol.step_size)) \
            if data['side'] == Order.BUY else \
            str(get_presentation_amount(Decimal(data['fee_amount']), trade.symbol.tick_size))
        return data

    class Meta:
        model = FillOrder
        fields = ('created', 'coin', 'pair', 'side', 'amount', 'pair_amount', 'fee_amount',)
