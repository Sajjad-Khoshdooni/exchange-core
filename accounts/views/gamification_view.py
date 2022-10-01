from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.gamification.gamify import get_groups_data


class GamificationAPIView(APIView):

    def get(self, request):
        active = request.query_params.get('active') == '1'

        account = request.user.account
        return Response(get_groups_data(account, only_active=active))
