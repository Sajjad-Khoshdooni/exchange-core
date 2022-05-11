from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.views.authentication import CustomTokenAuthentication
from ledger.views.wallet_view import WalletSerializer
from accounts.models import Account, User
from ledger.models import Wallet
from ledger.utils.liquidation import get_wallet_balances


class BalanceInformationSerializer(serializers.ModelSerializer):

    wallet = serializers.SerializerMethodField()

    def get_wallet(self, user: User):
        pos_wallet = []
        wallets = user.account.wallet_set.all()
        for wallet in wallets:
            if wallet.get_free() > 0:
                pos_wallet.append(wallet)

        user = WalletSerializer(instance=pos_wallet, many=True).data
        return user

    class Meta:
        model = User
        fields = ('wallet',)


class GetBalanceInformation(ListAPIView):

    authentication_classes = (SessionAuthentication, CustomTokenAuthentication)
    permission_classes = (IsAuthenticated,)

    serializer_class = BalanceInformationSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
