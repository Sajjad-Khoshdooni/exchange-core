from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.gamification.gamify import condition_groups, ConditionGroup, Condition


class BannerAlertAPIView(APIView):
    def get(self, request):

        return Response({
            'banner': self.get_alert_condition()
        })

    def get_alert_condition(self):
        account = self.request.user.account

        for group in condition_groups:  # type: ConditionGroup
            for condition_cls in group.conditions:
                goal = condition_cls(account)  # type: Condition

                if not goal.finished():
                    return goal.get_alert_dict()
