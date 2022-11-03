from django.shortcuts import redirect

from experiment.models.click import Click
from experiment.models.link import Link


def deposit_experiment_view(request, token):
    link = Link.objects.filter(token=token).first()
    if link:
        Click.objects.create(user_agent=str(request.user_agent), link=link)

        response = redirect(link.destination)
        return response
