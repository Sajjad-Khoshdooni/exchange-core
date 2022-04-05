import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView

from accounts.models import VerificationCode
from accounts.verifiers.legal import is_48h_rule_passed
from financial.utils.withdraw_limit import user_reached_crypto_withdraw_limit
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Network, Transfer, NetworkAsset, AddressBook
from ledger.utils.laundering import check_withdraw_laundering
from ledger.utils.precision import get_precision
from ledger.utils.price import get_trading_price_irt, BUY


class WithdrawSerializer(serializers.ModelSerializer):
    address_book_id = serializers.CharField(write_only=True, required=False, default=None)
    coin = serializers.CharField(write_only=True, required=False)
    network = serializers.CharField(write_only=True, required=False)
    code = serializers.CharField(write_only=True, required=True)
    address = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        user = self.context['request'].user
        account = user.account

        if attrs['address_book_id']:
            address_book = get_object_or_404(AddressBook, id=attrs['address_book_id'], account=account)

            address = address_book.address
            network = address_book.network

            if address_book.asset:
                asset = address_book.asset
            else:
                if not 'coin' in attrs:
                    raise ValidationError('رمزارزی انتخاب نشده است.')
                asset = get_object_or_404(Asset, symbol=attrs['coin'])
        else:
            if not 'coin' in attrs:
                raise ValidationError('رمزارزی انتخاب نشده است.')
            if not 'network' in attrs:
                raise ValidationError('شبکه‌ای انتخاب نشده است.')
            if not 'address' in attrs:
                raise ValidationError('آدرس وارد نشده است.')

            asset = get_object_or_404(Asset, symbol=attrs['coin'])
            network = get_object_or_404(Network, symbol=attrs['network'])
            address = attrs['address']

        if not address:
            raise ValidationError('آدرس وارد نشده است.')
        if not network:
            raise ValidationError('شبکه‌ای انتخاب نشده است.')
        if not asset:
            raise ValidationError('رمزارزی انتخاب نشده است.')

        if not re.match(network.address_regex, address):
            raise ValidationError('آدرس به فرمت درستی وارد نشده است.')

        if asset.symbol == Asset.IRT:
            raise ValidationError('نشانه دارایی اشتباه است.')

        code = attrs['code']
        otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_WITHDRAW)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

        if not is_48h_rule_passed(user):
            raise ValidationError('از اولین واریز ریالی حداقل باید دو روز کاری بگذرد.')

        network_asset = get_object_or_404(NetworkAsset, asset=asset, network=network)

        amount = attrs['amount']

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
        fields = ('amount', 'address', 'coin', 'network', 'code', 'address_book_id')


class WithdrawView(CreateAPIView):
    serializer_class = WithdrawSerializer
    queryset = Transfer.objects.all()

