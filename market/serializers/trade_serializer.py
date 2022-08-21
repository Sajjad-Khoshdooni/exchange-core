from decimal import Decimal

from rest_framework import serializers

from ledger.models import Asset
from ledger.models.asset import AssetSerializerMini
from ledger.utils.precision import floor_precision
from market.models import Trade, Order


class AccountTradeSerializer(serializers.ModelSerializer):
    coin = serializers.CharField(source='symbol.asset.symbol')
    pair = serializers.CharField(source='symbol.base_asset.symbol')
    pair_amount = serializers.CharField(source='base_amount')
    market = serializers.SerializerMethodField()

    def get_market(self, instance: Trade):
        return instance.order.wallet.market

    def to_representation(self, trade: Trade):
        data = super(AccountTradeSerializer, self).to_representation(trade)
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
        model = Trade
        fields = ('created', 'coin', 'pair', 'side', 'amount', 'price', 'pair_amount', 'fee_amount', 'market')


class TradeSerializer(AccountTradeSerializer):
    coin = serializers.CharField(source='symbol.asset.symbol')
    pair = serializers.CharField(source='symbol.base_asset.symbol')
    pair_amount = serializers.CharField(source='base_amount')
    is_buyer_maker = serializers.SerializerMethodField()

    asset = AssetSerializerMini(source='symbol.asset', read_only=True)
    base_asset = AssetSerializerMini(source='symbol.base_asset', read_only=True)

    @classmethod
    def get_is_buyer_maker(cls, instance: Trade):
        return (instance.side == Order.BUY) == instance.is_maker

    class Meta:
        model = Trade
        fields = ('created', 'coin', 'pair', 'amount', 'price', 'pair_amount', 'is_buyer_maker')
