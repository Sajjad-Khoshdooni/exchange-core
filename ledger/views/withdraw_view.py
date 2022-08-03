import re

from decouple import config
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import VerificationCode
from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.verifiers.legal import is_48h_rule_passed
from accounts.views.authentication import CustomTokenAuthentication
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
    code = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    memo = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):

        if config('WITHDRAW_ENABLE', '1') == '0':
            raise ValidationError('در حال حاضر امکان برداشت وجود ندارد.')

        user = self.context['request'].user

        if user.level < user.LEVEL2 and not user.allow_level1_crypto_withdraw:
            raise ValidationError('برای برداشت ابتدا احراز هویت نمایید.')

        account = user.account
        api = self.context.get('api')
        if attrs['address_book_id'] and (not api):

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
            if 'coin' not in attrs:
                raise ValidationError('رمزارزی انتخاب نشده است.')
            if 'network' not in attrs:
                raise ValidationError('شبکه‌ای انتخاب نشده است.')
            if 'address' not in attrs:
                raise ValidationError('آدرس وارد نشده است.')

            if not api and 'code' not in attrs:
                raise ValidationError('کد وارد نشده است.')
            asset = get_object_or_404(Asset, symbol=attrs['coin'])
            network = get_object_or_404(Network, symbol=attrs['network'])
            address = attrs['address']

        if not re.match(network.address_regex, address):
            raise ValidationError('آدرس به فرمت درستی وارد نشده است.')

        if asset.symbol == Asset.IRT:
            raise ValidationError('نشانه دارایی اشتباه است.')

        memo = attrs.get('memo') or ''

        if not api:
            code = attrs['code']
            otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_CRYPTO_WITHDRAW)

            if not otp_code:
                raise ValidationError({'code': 'کد نامعتبر است.'})

        if not is_48h_rule_passed(user):
            raise ValidationError('از اولین واریز ریالی حداقل باید دو روز کاری بگذرد.')

        network_asset = get_object_or_404(NetworkAsset, asset=asset, network=network)

        amount = attrs['amount']

        if get_precision(amount) > network_asset.withdraw_precision:
            raise ValidationError('مقدار وارد شده اشتباه است.')

        if amount < network_asset.withdraw_min:
            raise ValidationError('مقدار وارد شده کوچک است.')

        if amount > network_asset.withdraw_max:
            raise ValidationError('مقدار وارد شده بزرگ است.')

        wallet = asset.get_wallet(account)

        if not check_withdraw_laundering(wallet=wallet, amount=amount):
            raise ValidationError(
                'در این سطح کاربری نمی‌توانید ریال واریزی را به صورت رمزارز برداشت کنید. لطفا احراز هویت سطح ۳ را انجام دهید.')

        irt_value = get_trading_price_irt(asset.symbol, BUY, raw_price=False) * amount

        if user_reached_crypto_withdraw_limit(user, irt_value):
            raise ValidationError({'amount': 'شما به سقف برداشت رمزارزی خورده اید.'})

        if not api:
            otp_code.set_code_used()

        return {
            'network': network,
            'asset': asset,
            'wallet': wallet,
            'amount': amount,
            'out_address': address,
            'account': account,
            'memo': memo
        }

    def create(self, validated_data):
        try:
            return Transfer.new_withdraw(
                wallet=validated_data['wallet'],
                network=validated_data['network'],
                amount=validated_data['amount'],
                address=validated_data['out_address'],
                memo=validated_data['memo'],
            )
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')

    class Meta:
        model = Transfer
        fields = ('amount', 'address', 'coin', 'network', 'code', 'address_book_id', 'memo',)


class WithdrawView(CreateAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]
    serializer_class = WithdrawSerializer
    queryset = Transfer.objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.auth:
            ctx['api'] = 1
        return ctx
