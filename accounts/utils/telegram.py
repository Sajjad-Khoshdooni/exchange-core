import requests
from django.conf import settings
from yekta_config import secret
from yekta_config.config import config


def send_support_message(message: str, link: str):
    text = message + '\n' + link

    # to receive chat_id call https://api.telegram.org/bot{token}/getUpdates
    if settings.DEBUG:
        print('Sending support...')
        print(text)
        return

    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}'.format(
        token=secret('TELEGRAM_SUPPORT_BOT_TOKEN'),
        chat_id=config('TELEGRAM_SUPPORT_CHAT_ID'),
        text=text,
    )

    return requests.get(url, timeout=5)


def send_system_message(message: str, link: str):
    text = message + '\n' + link

    if settings.DEBUG:
        print('Sending system...')
        print(text)
        return

    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}'.format(
        token=secret('TELEGRAM_SYSTEM_BOT_TOKEN'),
        chat_id=config('TELEGRAM_SYSTEM_CHAT_ID'),
        text=text
    )

    return requests.get(url, timeout=5)
