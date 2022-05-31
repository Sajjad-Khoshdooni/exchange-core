from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.views.authentication import CustomTokenAuthentication
from ledger.views.wallet_view import WalletSerializer


class BalanceInformationSerializer(serializers.ModelSerializer):
    wallet = serializers.SerializerMethodField()

    def get_wallet(self, user: User):
        not_zero_wallet = []
        wallets = user.account.wallet_set.all().select_related('assset')
        for wallet in wallets:
            if wallet.get_free() > 0:
                not_zero_wallet.append(wallet)

        user = WalletSerializer(instance=not_zero_wallet, many=True).data
        return user

    class Meta:
        model = User
        fields = ('wallet',)


class GetBalanceInformation(ListAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication)
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    serializer_class = BalanceInformationSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
