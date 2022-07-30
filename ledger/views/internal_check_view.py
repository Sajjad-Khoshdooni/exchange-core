from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.models import Transfer


class InternalCheckView(APIView):

    def get(self, request):
        id = request.GET['id']

        transfer = Transfer.objects.get(id=id)

        if not transfer:
            return Response(404)

        return Response({
            'internal': transfer.source == Transfer.INTERNAL
        }, 200)
