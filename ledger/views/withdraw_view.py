import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView

from accounts.models import VerificationCode
from accounts.verifiers.legal import is_48h_rule_passed
from financial.utils.withdraw_limit import user_reached_crypto_withdraw_limit
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Network, Transfer, NetworkAsset
from ledger.utils.laundering import check_withdraw_laundering
from ledger.utils.precision import get_precision
from ledger.utils.price import get_trading_price_irt, BUY


class WithdrawSerializer(serializers.ModelSerializer):
    address = serializers.CharField(write_only=True)
    coin = serializers.CharField(write_only=True)
    network = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        user = self.context['request'].user
        account = user.account
        asset = get_object_or_404(Asset, symbol=attrs['coin'])

        if asset.symbol == Asset.IRT:
            raise ValidationError('نشانه دارایی اشتباه است.')

        code = attrs['code']
        otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_WITHDRAW)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

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

        irt_value = get_trading_price_irt(asset.symbol, BUY, raw_price=False) * amount

        if user_reached_crypto_withdraw_limit(user, irt_value):
            raise ValidationError({'amount': 'شما به سقف برداشت رمزارزی خورده اید.'})

        otp_code.set_code_used()

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
        fields = ('amount', 'address', 'coin', 'network', 'code')


class WithdrawView(CreateAPIView):
    serializer_class = WithdrawSerializer

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }