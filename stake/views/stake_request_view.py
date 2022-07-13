from django.db import transaction
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.utils import email
from ledger.models import Wallet, Trx
from ledger.utils.wallet_pipeline import WalletPipeline
from stake.models import StakeRequest, StakeOption
from stake.views.stake_option_view import StakeOptionSerializer


class StakeRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    stake_option = serializers.CharField(write_only=True)
    stake_option_data = serializers.SerializerMethodField()

    def get_stake_option_data(self, *args, **kwargs):
        stake_request = args[0]
        return StakeOptionSerializer(instance=StakeOption.objects.filter(
            stakerequest=stake_request), many=True).data

    def validate(self, attrs):
        stake_option = StakeOption.objects.get(id=attrs['stake_option'])
        amount = attrs['amount']
        user = self.context['request'].user
        asset = stake_option.asset
        wallet = asset.get_wallet(user.account)
        if wallet.get_free() < amount:
            raise ValidationError('مقدار وارد شده از موجودی کیف پول شما بیشتر است.')

        if not stake_option.enable:
            raise ValidationError('امکان استفاده از این اپشن در حال حاضر وجود ندارد.')

        return {
            'stake_option': stake_option,
            'amount': amount,
            'account': user.account,
            'wallet': wallet,
            'user': user
        }

    def create(self, validated_data):
        stake_option = validated_data['stake_option']
        amount = validated_data['amount']
        user = validated_data['user']

        account = user.account
        asset = stake_option.asset

        spot_wallet = asset.get_wallet(account)
        stake_wallet = asset.get_wallet(account=account, market=Wallet.STAKE)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            stake_object = StakeRequest.objects.create(
                stake_option=stake_option,
                amount=amount,
                account=user.account
            )
            pipeline.new_trx(
                group_id=stake_object.group_id,
                sender=spot_wallet,
                receiver=stake_wallet,
                amount=amount,
                scope=Trx.STAKE
            )

        return stake_object

    class Meta:
        model = StakeRequest
        fields = ('status', 'stake_option', 'amount', 'stake_option', 'stake_option_data')


class StakeRequestAPIView(ModelViewSet):
    serializer_class = StakeRequestSerializer

    def get_queryset(self):
        return StakeRequest.objects.filter(account=self.request.user.account)

    def destroy(self, request, *args, **kwargs):

        instance = StakeRequest.objects.get(pk=kwargs['pk'], account=self.request.user.account)

        if instance.status not in (StakeRequest.PROCESS, StakeRequest.PENDING, StakeRequest.DONE):
            raise ValidationError('لغو این درخواست ممکن نیست.')

        instance.status = StakeRequest.CANCEL_PROCESS
        instance.save()

        return Response({'msg': 'stake_request canceled'}, status=status.HTTP_204_NO_CONTENT)