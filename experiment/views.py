from django.shortcuts import redirect

from experiment.models.click import Click
from experiment.models.link import Link


def deposit_experiment_view(request, token):
    link = Link.objects.filter(token=token).first()
    if link:
        click = Click.objects.create(user_agent=str(request.user_agent))
        link.click = click
        link.save(update_fields=['click'])

        response = redirect(link.destination)
        return response