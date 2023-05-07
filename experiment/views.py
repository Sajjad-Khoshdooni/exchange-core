import logging

from decouple import config
from django.shortcuts import redirect

from experiment.models.click import Click
from experiment.models.link import Link


logger = logging.getLogger(__name__)


def click_view(request, token: str):
    link = Link.objects.filter(token=token).first()
    if link:
        Click.objects.create(user_agent=request.META['HTTP_USER_AGENT'], link=link)
        response = redirect(config('EXPERIMENT_DEPOSIT_URL'))
    else:
        response = redirect(config('PANEL_URL'))

    return response
