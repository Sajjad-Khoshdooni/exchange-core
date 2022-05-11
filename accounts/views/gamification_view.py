from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.gamification.gamify import condition_groups


class GamificationAPIView(APIView):

    def get(self, request):

        account = request.user.account

        groups = []

        for group in condition_groups:
            groups.append(
                group.as_dict(account)
            )

        return Response(groups)



