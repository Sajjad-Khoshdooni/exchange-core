import logging

import requests
from django.conf import settings
from yekta_config import secret
from yekta_config.config import config

logger = logging.getLogger(__name__)


def send_support_message(message: str, link: str):
    text = message + '\n' + link

    # to receive chat_id call https://api.telegram.org/bot{token}/getUpdates
    if settings.DEBUG_OR_TESTING:
        print('Sending support...')
        print(text)
        return

    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}'.format(
        token=secret('TELEGRAM_SUPPORT_BOT_TOKEN'),
        chat_id=config('TELEGRAM_SUPPORT_CHAT_ID'),
        text=text,
    )

    try:
        return requests.get(url, timeout=5)
    except:
        logger.warning('Failed to send telegram support')


def send_system_message(message: str, link: str):
    text = message + '\n' + link

    if settings.DEBUG_OR_TESTING:
        print('Sending system...')
        print(text)
        return

    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}'.format(
        token=secret('TELEGRAM_SYSTEM_BOT_TOKEN'),
        chat_id=config('TELEGRAM_SYSTEM_CHAT_ID'),
        text=text
    )

    try:
        return requests.get(url, timeout=5)
    except:
        logger.warning('Failed to send telegram system')
