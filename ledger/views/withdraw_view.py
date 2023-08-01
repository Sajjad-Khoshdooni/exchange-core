import re
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, CreateAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.authentication import CustomTokenAuthentication
from accounts.models import VerificationCode, LoginActivity
from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from accounts.verifiers.legal import is_48h_rule_passed
from financial.utils.withdraw_limit import user_reached_crypto_withdraw_limit
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Transfer, NetworkAsset, AddressBook, DepositAddress
from ledger.models.asset import CoinField
from ledger.models.network import NetworkField
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.laundering import check_withdraw_laundering
from ledger.utils.precision import get_precision
from ledger.utils.withdraw_verify import can_withdraw
from ledger.views.address_book_view import AddressBookCreateSerializer


class WithdrawSerializer(serializers.ModelSerializer):
    address_book_id = serializers.CharField(write_only=True, required=False, default=None)
    coin = CoinField(source='asset', required=False)
    network = NetworkField(required=False)
    code = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(source='out_address', required=False)
    memo = serializers.CharField(required=False, allow_blank=True)
    address_book = serializers.SerializerMethodField()
    totp = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        request = self.context['request']
        user = request.user

        if not can_withdraw(user.get_account(), request) or not user.can_withdraw_crypto:
            raise ValidationError('امکان برداشت وجود ندارد.')

        account = user.get_account()
        from_panel = self.context.get('from_panel')
        asset = attrs.get('asset')
        network = attrs.get('network')
        address = attrs.get('out_address')
        address_book = None
        totp = attrs.get('totp', None)

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
            if not network:
                raise ValidationError('شبکه‌ای انتخاب نشده است.')
            if not address:
                raise ValidationError('آدرس وارد نشده است.')

            if from_panel and 'code' not in attrs:
                raise ValidationError('کد وارد نشده است.')

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
            if not user.is_2fa_valid(totp):
                raise ValidationError({'otp' : ' رمز موقت نامعتبر است.'})


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
            'memo': memo,
            'address_book': address_book,
        }

    def create(self, validated_data):
        try:
            transfer = Transfer.new_withdraw(
                wallet=validated_data['wallet'],
                network=validated_data['network'],
                amount=validated_data['amount'],
                address=validated_data['out_address'],
                memo=validated_data['memo'],
            )

            transfer.login_activity = LoginActivity.from_request(request=self.context['request'])
            transfer.address_book = validated_data['address_book']
            transfer.save(update_fields=['address_book', 'login_activity'])

            return transfer
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')

    def get_address_book(self, transfer: Transfer):
        if transfer.address_book:
            return AddressBookCreateSerializer(transfer.address_book).data

    class Meta:
        model = Transfer
        fields = ('id', 'amount', 'address', 'coin', 'network', 'code', 'address_book_id', 'address_book', 'memo',
                  'totp')
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
