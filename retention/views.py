import logging

from django.conf import settings
from django.shortcuts import redirect

from retention.models import Link, Click

logger = logging.getLogger(__name__)


def click_view(request, token: str):
    link = Link.objects.filter(token=token).first()

    if link:
        Click.objects.create(user_agent=request.META['HTTP_USER_AGENT'], link=link)
        next_url = settings.PANEL_URL + Link.SCOPE_TO_LINK[link.scope]
        response = redirect(next_url)
    else:
        response = redirect(settings.PANEL_URL)

    return response
