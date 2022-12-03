import logging

import requests
from decouple import config

logger = logging.getLogger(__name__)


def send_message(profile: str, text: str):
    token = config('KAFTAR_TOKEN', default='')

    if not profile or not token:
        logger.info('No kaftar token set!')
        return

    requests.post(
        'https://kaftar.raastin.com/api/v1/messaging/send/',
        headers={
            'Authorization': token
        },
        data={
            'profile': profile,
            'text': text
        }
    )
