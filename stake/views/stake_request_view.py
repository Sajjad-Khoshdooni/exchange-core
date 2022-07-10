from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet
from stake.models import StakeRequest, StakeOption


class StakeRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    stake_option = serializers.CharField()
    group_id = serializers.CharField(read_only=True)

    def validate(self, attrs):
        stake_option = StakeOption.objects.get(id=attrs['stake_option'])
        amount = attrs['amount']
        user = self.context['request'].user
        asset = stake_option.asset

        if asset.get_wallet(user.account).get_free() < amount:
            raise ValidationError('مقدار وارد شده از موجودی کیف پول شما بیشتر است.')

        if not stake_option.enable:
            raise ValidationError('امکان استفاده از این اپشن در حال حاضر وجود ندارد.')

        return {
            'stake_option': stake_option,
            'amount': amount,
            'account': user.account
        }

    class Meta:
        model = StakeRequest
        fields = ('status', 'stake_option', 'amount', 'group_id')


class StakeRequestAPIView(ModelViewSet):
    serializer_class = StakeRequestSerializer

    def get_queryset(self):
        return StakeRequest.objects.filter(account=self.request.user.account    )

