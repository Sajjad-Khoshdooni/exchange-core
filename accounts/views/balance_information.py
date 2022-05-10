from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.liquidation import get_wallet_balances


class GetBalanceInformation(APIView):

    def get(self):
        account = self.request.user.account
        resp = get_wallet_balances(account=account, market=Wallet.SPOT)
        return Response()


