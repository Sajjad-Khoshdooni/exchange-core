from rest_framework.views import APIView

from experiment.models.click import Click
from experiment.models.link import Link


class DepositExperimentView(APIView):
    def post(self, request, token):
        link = Link.objects.filter(token=token).first()
        if link:
            click = Click.objects.create(user_agent=str(request.user_agent))
            link.click = click
            link.save(update_fields=['click'])
