import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView

from accounts.verifiers.legal import is_48h_rule_passed
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Network, Transfer, NetworkAsset
from ledger.utils.laundering import check_withdraw_laundering
from ledger.utils.precision import get_precision


class WithdrawSerializer(serializers.ModelSerializer):
    address = serializers.CharField(write_only=True)
    coin = serializers.CharField(write_only=True)
    network = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        account = user.account
        asset = get_object_or_404(Asset, symbol=attrs['coin'])

        if asset.symbol == Asset.IRT:
            raise ValidationError('نشانه دارایی اشتباه است.')

        if not is_48h_rule_passed(user):
            raise ValidationError('از اولین واریز ریالی حداقل باید دو روز کاری بگذرد.')

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

        wallet = asset.get_wallet(account)

        if not check_withdraw_laundering(wallet=wallet, amount=amount):
            raise ValidationError('در این سطح کاربری نمی‌توانید ریال واریزی را به صورت رمزارز برداشت کنید.')

        return {
            'network': network,
            'asset': asset,
            'wallet': wallet,
            'amount': amount,
            'out_address': address,
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
    serializer_class = WithdrawSerializer
