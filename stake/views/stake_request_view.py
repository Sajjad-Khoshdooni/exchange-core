from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.utils import email
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from ledger.models import Wallet, Trx
from ledger.utils.wallet_pipeline import WalletPipeline
from stake.models import StakeRequest, StakeOption, StakeRevenue
from stake.views.stake_option_view import StakeOptionSerializer


class StakeRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    stake_option = serializers.CharField(write_only=True)
    stake_option_data = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()

    def get_stake_option_data(self, *args, **kwargs):
        stake_request = args[0]
        return StakeOptionSerializer(instance=StakeOption.objects.filter(
            stakerequest=stake_request), many=True).data

    def get_total_revenue(self, *args):
        stake_request = args[0]
        return StakeRevenue.objects.filter(stake_request=stake_request).aggregate(Sum('revenue'))['revenue__sum']

    def validate(self, attrs):
        stake_option = StakeOption.objects.get(id=attrs['stake_option'])
        amount = attrs['amount']
        user = self.context['request'].user
        asset = stake_option.asset
        wallet = asset.get_wallet(user.account)

        if not stake_option.enable:
            raise ValidationError('امکان استفاده از این اپشن در حال حاضر وجود ندارد.')

        if not wallet.has_balance(amount=amount):
            raise ValidationError('مقدار وارد شده از موجودی کیف پول شما بیشتر است.')

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
        link = url_to_edit_object(stake_object)
        send_support_message(
            message='ثبت درخواست staking برای {} {}'.format(stake_object.stake_option.asset, stake_object.amount,),
            link=link
        )
        return stake_object

    class Meta:
        model = StakeRequest
        fields = ('status', 'stake_option', 'amount', 'stake_option', 'stake_option_data', 'total_revenue')


class StakeRequestAPIView(ModelViewSet):
    serializer_class = StakeRequestSerializer


    def get_queryset(self):
        return StakeRequest.objects.filter(account=self.request.user.account)

    def destroy(self, request, *args, **kwargs):

        instance = StakeRequest.objects.get(pk=kwargs['pk'], account=self.request.user.account)

        if instance.status == StakeRequest.PROCESS:
            instance.change_status(new_status=StakeRequest.CANCEL_COMPLETE)

        elif instance.status in (StakeRequest.PENDING, StakeRequest.DONE):
            instance.change_status(new_status=StakeRequest.CANCEL_PROCESS)

        else:
            raise ValidationError('امکان ارسال درخواست لغو وجود ندارد.')

        return Response({'msg': 'stake_request canceled'}, status=status.HTTP_204_NO_CONTENT)
