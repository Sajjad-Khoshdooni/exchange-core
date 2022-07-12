import requests
from django.conf import settings
from oauth2client.service_account import ServiceAccountCredentials
from yekta_config.config import config

from accounts.models import User


def _get_access_token():
    SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

    file_path = config('FIREBASE_SECRET_FILE_PATH')

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        file_path, SCOPES)
    access_token_info = credentials.get_access_token()

    return access_token_info.access_token


def send_push_notif_to_user(user: User, title: str, body: str, image: str = None, link: str = None):
    from accounts.models import FirebaseToken

    fire_base_token = FirebaseToken.objects.filter(user=user).last()

    send_push_notif(fire_base_token.token,  title, body, image, link)


def send_push_notif(token: str, title: str, body: str, image: str = None, link: str = None):
    notification = {
        "body": body,
        "title": title
    }

    if image:
        notification['image'] = image

    body = {
        "token": token,
        "notification": notification
    }

    if link:
        body['webpush'] = {
            'fcm_options': {
                'link': link
            }
        }

    resp = requests.post(
        url=' https://fcm.googleapis.com/v1/projects/raastin-7203e/messages:send',
        headers={
            'Authorization': 'Bearer ' + _get_access_token(),
            'Content-Type': 'application/json; UTF-8',
        },
        json={
            'message': body
        }
    )

    if not resp.ok:
        print(body)
        print(resp.status_code)
        print(resp.json())

    return resp


to_signup_message = """
همین حالا ثبت‌نام کن و شیبا بگیر.
فقط تا آخر هفته
"""


def alert_shib_prize_to_signup(token: str):
    send_push_notif(
        token=token,
        title='تا ۲۰۰,۰۰۰ شیبا هدیه بگیرید',
        body=to_signup_message.strip(),
        image=settings.HOST_URL + '/static/ads/shiba-prize.png',
        link='https://raastin.com/auth/register?rewards=true&utm_source=push&utm_medium=push&utm_campaign=signup'
    )


to_trade_message = """
همین حالا معامله کن و شیبا بگیر.
فقط تا آخر هفته
"""


def alert_shib_prize_to_engagement(user: User):
    send_push_notif_to_user(
        user=user,
        title='تا ۲۰۰,۰۰۰ شیبا هدیه بگیرید',
        body=to_trade_message.strip(),
        image=settings.HOST_URL + '/static/ads/shiba-prize.png',
        link='https://raastin.com/trade/market/BTCIRT?utm_source=push&utm_medium=push&utm_campaign=trade'
    )
