from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.gamification.gamify import goal_groups
from accounts.gamification.goals import GoalGroup, Goal, RedeemPrize
from ledger.models import Prize


class BannerAlertAPIView(APIView):
    def get(self, request):

        return Response({
            'banner': self.get_alert_condition()
        })

    def get_alert_condition(self):
        account = self.request.user.account

        if Prize.objects.filter(account=account, fake=False, redeemed=False).exists():
            goal = RedeemPrize(account)
            return goal.get_alert_dict()

        for group in goal_groups:  # type: GoalGroup
            for condition_cls in group.conditions:
                goal = condition_cls(account)  # type: Goal

                if not goal.finished():
                    return goal.get_alert_dict()
