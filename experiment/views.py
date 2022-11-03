import logging

from django.shortcuts import redirect
from yekta_config.config import config

from experiment.models.click import Click
from experiment.models.link import Link


logger = logging.getLogger(__name__)


def click_view(request, token):
    link = Link.objects.filter(token=token).first()
    if link:
        Click.objects.create(user_agent=request.META['HTTP_USER_AGENT'], link=link)
        logger.info('LinkClickedSuccessfully', extra={
            'token': token
        })
        response = redirect(config('EXPERIMENT_DEPOSIT_URL'))
    else:
        logger.info('LinkObjectExistenceError', extra={
            'token': token
        })
        response = redirect('https://raastin.com/')

    return response

