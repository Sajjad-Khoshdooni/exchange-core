from decimal import Decimal

from rest_framework import serializers

from ledger.models import Asset
from ledger.utils.external_price import BUY
from ledger.utils.precision import floor_precision, decimal_to_str
from market.models import Trade, BaseTrade


class AccountTradeSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source='symbol.asset.symbol')
    base_asset = serializers.CharField(source='symbol.base_asset.symbol')
    base_amount = serializers.SerializerMethodField()

    def get_base_amount(self, trade: Trade):
        return trade.price * trade.amount

    def to_representation(self, trade: Trade):
        data = super(AccountTradeSerializer, self).to_representation(trade)
        amount = floor_precision(Decimal(data['amount']), trade.symbol.step_size)
        if not amount:
            amount = floor_precision(trade.symbol.min_trade_quantity, trade.symbol.step_size)
        data['amount'] = str(amount)
        data['price'] = decimal_to_str(floor_precision(Decimal(data['price']), trade.symbol.tick_size))
        data['base_amount'] = decimal_to_str(floor_precision(Decimal(data['base_amount']), trade.symbol.tick_size))

        if 'fee_amount' in data:
            if data['side'] == BUY:
                data['fee_amount'] = trade.symbol.asset.get_presentation_amount(data['fee_amount'])
            elif trade.symbol.base_asset.symbol == Asset.IRT:
                data['fee_amount'] = trade.symbol.asset.get_presentation_price_irt(data['fee_amount'])
            elif trade.symbol.base_asset.symbol == Asset.USDT:
                data['fee_amount'] = trade.symbol.asset.get_presentation_price_usdt(data['fee_amount'])
            data['fee_asset'] = data['asset'] if data['side'] == BUY else data['base_asset']
        return data

    class Meta:
        model = Trade
        fields = ('created', 'asset', 'base_asset', 'side', 'amount', 'price', 'base_amount', 'fee_amount', 'market')


class TradeSerializer(serializers.ModelSerializer):
    is_buyer_maker = serializers.SerializerMethodField()

    @classmethod
    def get_is_buyer_maker(cls, instance: Trade):
        return (instance.side == BUY) == instance.is_maker

    class Meta:
        model = Trade
        fields = ('created', 'amount', 'price', 'is_buyer_maker')

    def to_representation(self, trade: Trade):
        data = super().to_representation(trade)

        amount = floor_precision(Decimal(data['amount']), trade.symbol.step_size)

        if not amount:
            amount = floor_precision(trade.symbol.min_trade_quantity, trade.symbol.step_size)

        data['amount'] = str(amount)
        data['price'] = decimal_to_str(floor_precision(Decimal(data['price']), trade.symbol.tick_size))

        return data


class TradePairSerializer(TradeSerializer):
    symbol = serializers.CharField(source='symbol.name')
    client_order_id = serializers.SerializerMethodField()
    pair_order_id = serializers.SerializerMethodField()
    pair_client_order_id = serializers.SerializerMethodField()

    def get_client_order_id(self, instance: Trade):
        return self.context['client_order_id_mapping'].get(instance.order_id)

    def get_pair_order_id(self, instance: Trade):
        mapping = self.context['maker_taker_mapping'] if instance.is_maker else self.context['taker_maker_mapping']
        return mapping.get(instance.order_id)

    def get_pair_client_order_id(self, instance: Trade):
        return self.context['client_order_id_mapping'].get(self.get_pair_order_id(instance))

    class Meta:
        model = Trade
        fields = ('id', 'symbol', 'side', 'created', 'amount', 'price', 'is_maker', 'order_id', 'client_order_id',
                  'pair_order_id', 'pair_client_order_id')
