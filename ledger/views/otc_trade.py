from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.response import Response

from ledger.models import OTCRequest, Wallet, Order, Asset
from ledger.utils.price import get_trading_price


class OTCRequestSerializer(serializers.ModelSerializer):
    src = serializers.CharField(source='src_asset.symbol')
    dest = serializers.CharField(source='dest_asset.symbol')
    expire = serializers.SerializerMethodField()

    def validate(self, attrs):
        src = attrs['src_asset']['symbol']
        dest = attrs['dest_asset']['symbol']

        if Asset.IRT not in (src, dest):
            raise ValidationError('trade not supported')

        if src == dest:
            raise ValidationError('src and dest could not be equal')

        try:
            return {
                'src_asset': Asset.get(src),
                'dest_asset': Asset.get(dest),
            }
        except:
            raise ValidationError('Invalid src or dest symbol')

    def create(self, validated_data):
        request = self.context['request']

        src_asset = validated_data['src_asset']
        dest_asset = validated_data['dest_asset']

        price = get_trading_price(src_asset.symbol, dest_asset.symbol)

        return OTCRequest.objects.create(
            account=request.user.account,
            src_asset=src_asset,
            dest_asset=dest_asset,
            price=price
        )

    def get_expire(self, otc: OTCRequest):
        return otc.created + timedelta(seconds=OTCRequest.EXPIRE_TIME)

    class Meta:
        model = OTCRequest
        fields = ('src', 'dest', 'token', 'price', 'expire')
        read_only_fields = ('token', 'price')


class OTCTradeRequestView(CreateAPIView):
    serializer_class = OTCRequestSerializer


# class