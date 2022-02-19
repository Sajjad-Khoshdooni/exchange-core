import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView

from accounts.permissions import IsBasicVerified
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Network, Transfer, NetworkAsset
from ledger.utils.precision import get_precision


class WithdrawSerializer(serializers.ModelSerializer):
    address = serializers.CharField(write_only=True)
    coin = serializers.CharField(write_only=True)
    network = serializers.CharField(write_only=True)

    def validate(self, attrs):
        account = self.context['request'].user.account
        asset = get_object_or_404(Asset, symbol=attrs['coin'])

        if asset.symbol == Asset.IRT:
            raise ValidationError('نشانه دارایی اشتباه است.')

        network = get_object_or_404(Network, symbol=attrs['network'])

        network_asset = get_object_or_404(NetworkAsset, asset=asset, network=network)

        address = attrs['address']
        amount = attrs['amount']

        if not re.match(network.address_regex, address):
            raise ValidationError('آدرس به فرمت درستی وارد نشده است.')

        if get_precision(amount) > asset.precision:
            raise ValidationError('مقدار وارد شده اشتباه است.')

        if amount < network_asset.withdraw_min:
            raise ValidationError('مقدار وارد شده کوچک است.')

        if amount > network_asset.withdraw_max:
            raise ValidationError('مقدار وارد شده بزرگ است.')

        return {
            'network': network,
            'asset': asset,
            'wallet': asset.get_wallet(account),
            'amount': attrs['amount'],
            'out_address': attrs['address'],
            'account': account,
        }

    def create(self, validated_data):
        try:
            return Transfer.new_withdraw(
                wallet=validated_data['wallet'],
                network=validated_data['network'],
                amount=validated_data['amount'],
                address=validated_data['out_address']
            )
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')

    class Meta:
        model = Transfer
        fields = ('amount', 'address', 'coin', 'network')


class WithdrawView(CreateAPIView):
    permission_classes = (IsBasicVerified, )
    serializer_class = WithdrawSerializer
