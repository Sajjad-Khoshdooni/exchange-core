import re

from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.authentication import CustomTokenAuthentication
from accounts.models import VerificationCode
from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from accounts.utils.auth2fa import is_2fa_active_for_user, code_2fa_verifier
from accounts.verifiers.legal import is_48h_rule_passed
from financial.utils.withdraw_limit import user_reached_crypto_withdraw_limit
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Network, Transfer, NetworkAsset, AddressBook, DepositAddress
from ledger.models.asset import CoinField
from ledger.models.network import NetworkField
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.laundering import check_withdraw_laundering
from ledger.utils.precision import get_precision
from ledger.utils.withdraw_verify import can_withdraw


class WithdrawSerializer(serializers.ModelSerializer):
    address_book_id = serializers.CharField(write_only=True, required=False, default=None)
    coin = CoinField(source='asset', required=False)
    network = NetworkField(required=False)
    code = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(required=False)
    memo = serializers.CharField(required=False, allow_blank=True)
    code_2fa = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context['request']
        user = request.user

        if not can_withdraw(user.get_account(), request) or not user.can_withdraw_crypto:
            raise ValidationError('امکان برداشت وجود ندارد.')

        account = user.get_account()
        from_panel = self.context.get('from_panel')
        asset = attrs.get('asset')

        if attrs['address_book_id'] and from_panel:
            address_book = get_object_or_404(AddressBook, id=attrs['address_book_id'], account=account)
            address = address_book.address
            network = address_book.network

            if address_book.asset:
                asset = address_book.asset
            else:
                if not asset:
                    raise ValidationError('رمزارزی انتخاب نشده است.')
        else:
            if not asset:
                raise ValidationError('رمزارزی انتخاب نشده است.')
            if 'network' not in attrs:
                raise ValidationError('شبکه‌ای انتخاب نشده است.')
            if 'address' not in attrs:
                raise ValidationError('آدرس وارد نشده است.')

            if from_panel and 'code' not in attrs:
                raise ValidationError('کد وارد نشده است.')

            network = get_object_or_404(Network, symbol=attrs['network'])
            address = attrs['address']

        if not re.match(network.address_regex, address):
            raise ValidationError('آدرس به فرمت درستی وارد نشده است.')

        if asset.symbol == Asset.IRT:
            raise ValidationError('نشانه دارایی اشتباه است.')

        memo = attrs.get('memo') or ''

        if from_panel:
            code = attrs['code']
            otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_CRYPTO_WITHDRAW)

            if not otp_code:
                raise ValidationError({'code': 'کد نامعتبر است.'})

            if is_2fa_active_for_user(user):
                code_2fa = attrs.get('code_2fa') or ''
                code_2fa_verifier(user_token=user.auth2fa.token, code_2fa=code_2fa)

        if not is_48h_rule_passed(user):
            raise ValidationError('از اولین واریز ریالی حداقل باید دو روز کاری بگذرد.')

        network_asset = get_object_or_404(NetworkAsset, asset=asset, network=network)
        amount = attrs['amount']

        if not network_asset.can_withdraw_enabled():
            raise ValidationError('در حال حاضر امکان برداشت {} روی شبکه {} وجود ندارد.'.format(asset.symbol, network.symbol))

        if get_precision(amount) > network_asset.withdraw_precision:
            raise ValidationError('مقدار وارد شده اشتباه است.')

        if amount < network_asset.withdraw_min:
            raise ValidationError('مقدار وارد شده کوچک است.')

        if amount > network_asset.withdraw_max:
            raise ValidationError('مقدار وارد شده بزرگ است.')

        if DepositAddress.objects.filter(address=address, address_key__deleted=True):
            raise ValidationError('آدرس برداشت نامعتبر است.')

        if DepositAddress.objects.filter(address=address, address_key__account=account):
            raise ValidationError('آدرس برداشت متعلق به خودتان است. لطفا آدرس دیگری را وارد نمایید.')

        wallet = asset.get_wallet(account)

        if wallet.market != wallet.SPOT:
            raise ValidationError('کیف پول نادرستی انتخاب شده است.')

        if not wallet.has_balance(amount):
            raise ValidationError('موجودی کافی نیست.')

        if asset.enable and not check_withdraw_laundering(wallet=wallet, amount=amount):
            raise ValidationError(
                'در این سطح کاربری نمی‌توانید ریال واریزی را به صورت رمزارز برداشت کنید. لطفا احراز هویت سطح ۳ را انجام دهید.')

        price = get_external_price(asset.symbol, base_coin=Asset.IRT, side=BUY, allow_stale=True)

        if price:
            irt_value = price * amount

            if user_reached_crypto_withdraw_limit(user, irt_value):
                raise ValidationError({'amount': 'شما به سقف برداشت رمزارزی خود رسیده اید.'})

        if from_panel:
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
        fields = ('id', 'amount', 'address', 'coin', 'network', 'code', 'address_book_id', 'memo', 'code_2fa')
        ref_name = 'Withdraw Serializer'


class WithdrawView(CreateAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]
    serializer_class = WithdrawSerializer
    queryset = Transfer.objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['from_panel'] = not self.request.auth
        return ctx
