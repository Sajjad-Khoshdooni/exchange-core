import logging
from decimal import Decimal

from decouple import Csv, config
from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404

from accounts.authentication import CustomTokenAuthentication
from ledger.models import Network, Asset, DepositAddress, AddressKey, NetworkAsset
from ledger.models.transfer import Transfer
from ledger.requester.architecture_requester import request_architecture
from ledger.utils.external_price import get_external_price, SELL
from ledger.utils.ip_check import get_ip_address
from ledger.utils.precision import zero_by_precision
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class DepositSerializer(serializers.ModelSerializer):
    network = serializers.CharField(max_length=16, write_only=True)
    sender_address = serializers.CharField(max_length=256, write_only=True)
    receiver_address = serializers.CharField(max_length=256, write_only=True)
    coin = serializers.CharField(max_length=8, write_only=True)

    class Meta:
        model = Transfer
        fields = ['status', 'amount', 'trx_hash', 'block_hash',
                  'block_number', 'network', 'sender_address', 'receiver_address', 'coin']

    def create(self, validated_data):
        network_symbol = validated_data.get('network')
        sender_address = validated_data.get('sender_address')
        receiver_address = validated_data.get('receiver_address')
        network = Network.objects.get(symbol=network_symbol)

        deposit_address = DepositAddress.objects.filter(network=network, address=receiver_address).first()

        if not deposit_address:
            address_key = get_object_or_404(
                AddressKey,
                address=receiver_address,
                architecture=request_architecture(network)
            )
            deposit_address, _ = DepositAddress.objects.get_or_create(
                address=receiver_address,
                network=network,
                defaults={
                    'address_key': address_key
                }
            )

        coin = validated_data.get('coin')

        asset = Asset.objects.filter(symbol=coin).first()
        coin_mult = 1

        if not asset and coin:
            asset = Asset.objects.filter(original_symbol=coin).first()

            if asset:
                coin_mult = asset.get_coin_multiplier()

        if not asset:
            logger.warning('invalid coin for deposit', extra={'coin': coin})
            raise ValidationError({'coin': 'invalid coin'})

        wallet = asset.get_wallet(deposit_address.address_key.account)

        network_asset = get_object_or_404(NetworkAsset, asset=asset, network=network)

        if not network_asset.can_deposit_enabled():
            raise ValidationError({'deposit_enable': 'false'})

        status = validated_data.get('status')

        if status not in (Transfer.PENDING, Transfer.DONE, Transfer.CANCELED):
            raise ValidationError({'status': 'invalid status %s' % status})

        prev_transfer = Transfer.objects.filter(
            network=network,
            trx_hash=validated_data.get('trx_hash'),
            deposit=True
        ).order_by('-created').first()

        valid_transitions = [
            (Transfer.PENDING, Transfer.DONE),
            (Transfer.PENDING, Transfer.CANCELED),
        ]

        if prev_transfer:
            if prev_transfer.status == status:
                return prev_transfer

            if (prev_transfer.status, status) not in valid_transitions:
                raise ValidationError({
                    'status': 'invalid status transition (%s -> %s)' % (prev_transfer.status, status)
                })

            with WalletPipeline() as pipeline:
                prev_transfer.status = status

                if status in (Transfer.CANCELED, Transfer.DONE):
                    prev_transfer.finished_datetime = timezone.now()

                prev_transfer.save(update_fields=['status', 'finished_datetime'])

                if status == Transfer.DONE:
                    prev_transfer.build_trx(pipeline)

                    user = prev_transfer.wallet.account.user
                    user.first_crypto_deposit_date = timezone.now()
                    user.save(update_fields=['first_crypto_deposit_date'])

            prev_transfer.alert_user()

            return prev_transfer

        else:
            amount = Decimal(validated_data.get('amount')) / coin_mult

            if zero_by_precision(amount):
                raise ValidationError({'amount': 'small amount'})

            price_usdt = get_external_price(coin=asset.symbol, base_coin=Asset.USDT, side=SELL, allow_stale=True)
            price_irt = get_external_price(coin=asset.symbol, base_coin=Asset.IRT, side=SELL, allow_stale=True)

            with WalletPipeline() as pipeline:
                transfer, _ = Transfer.objects.get_or_create(
                    deposit=True,
                    trx_hash=validated_data.get('trx_hash'),
                    network=network,
                    wallet=wallet,
                    deposit_address=deposit_address,
                    out_address=sender_address,
                    defaults={
                        'amount': amount,
                        'block_hash': validated_data.get('block_hash'),
                        'block_number': validated_data.get('block_number'),
                        'usdt_value': amount * price_usdt,
                        'irt_value': amount * price_irt,
                    }
                )

                transfer.status = status

                if status in (Transfer.CANCELED, Transfer.DONE):
                    transfer.finished_datetime = timezone.now()

                transfer.save(update_fields=['status', 'finished_datetime'])

                if status == Transfer.DONE:
                    transfer.build_trx(pipeline)

                    user = transfer.wallet.account.user
                    user.first_crypto_deposit_date = timezone.now()
                    user.save(update_fields=['first_crypto_deposit_date'])

            transfer.alert_user()

            return transfer


class DepositTransferUpdateView(CreateAPIView, UserPassesTestMixin):
    authentication_classes = [CustomTokenAuthentication]
    serializer_class = DepositSerializer

    def test_func(self):
        permission_check = self.request.user.has_perm('ledger.add_transfer') and self.request.user.has_perm('ledger.change_transfer')
        ip_check = get_ip_address(self.request) in config('BLOCKLINK_IP', cast=Csv(), default='')

        return permission_check and ip_check
