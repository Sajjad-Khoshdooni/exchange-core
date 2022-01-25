from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.utils.margin import get_margin_info


class MarginInfoView(APIView):
    def get(self, request):
        account = request.user.account
        margin_info = get_margin_info(account)

        return Response({
            'total_assets': margin_info.total_assets,
            'total_debt': margin_info.total_debt,
            'margin_level': margin_info.get_margin_level(),
            'total_equity': margin_info.get_total_equity(),
        })
