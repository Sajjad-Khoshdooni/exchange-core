from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.utils.fields import AMOUNT_PRECISION


class DigitRequestView(APIView):
    def get(self):
        data = {
            'AMOUNT_PRECISION': AMOUNT_PRECISION
        }
        return Response(data, 200)
