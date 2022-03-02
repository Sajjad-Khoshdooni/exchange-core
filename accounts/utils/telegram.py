import requests
from yekta_config import secret
from yekta_config.config import config


def send_support_message(message: str, link: str):
    text = message + '\n' + link

    # to receive chat_id call https://api.telegram.org/bot{token}/getUpdates

    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}'.format(
        token=secret('TELEGRAM_SUPPORT_BOT_TOKEN'),
        chat_id=config('TELEGRAM_SUPPORT_CHAT_ID'),
        text=text,
    )

    return requests.get(url, timeout=5)


def send_system_message(message: str, link: str):
    text = message + '\n' + link

    url = 'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}'.format(
        token=secret('TELEGRAM_SYSTEM_BOT_TOKEN'),
        chat_id=config('TELEGRAM_SYSTEM_CHAT_ID'),
        text=text
    )

    return requests.get(url, timeout=5)
