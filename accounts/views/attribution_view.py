from rest_framework.response import Response
from rest_framework.views import APIView


class AttributionAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(status=200)
