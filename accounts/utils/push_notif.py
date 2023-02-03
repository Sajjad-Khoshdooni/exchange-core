import json

import requests
from decouple import config
from django.conf import settings
from oauth2client.service_account import ServiceAccountCredentials

from accounts.models import User


def _get_access_token():
    scopes = ['https://www.googleapis.com/auth/firebase.messaging']
    firebase_json = json.loads(config('FIREBASE_SECRET_JSON'))

    credentials = ServiceAccountCredentials._from_parsed_json_keyfile(firebase_json, scopes)
    access_token_info = credentials.get_access_token()

    return access_token_info.access_token


def send_push_notif_to_user(user: User, title: str, body: str, image: str = None, link: str = None):
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return

    from accounts.models import FirebaseToken

    firebase_token = FirebaseToken.objects.filter(user=user).last()

    if firebase_token:
        return send_push_notif(firebase_token.token,  title, body, image, link)


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
        },
        timeout=30,
    )

    if not resp.ok:
        print(body)
        print(resp.status_code)
        print(resp.json())

    if resp.status_code == 404:
        from accounts.models import FirebaseToken
        data = resp.json()

        if data['error']['status'] == 'NOT_FOUND':
            FirebaseToken.objects.filter(token=token).delete()

    return resp.ok


to_signup_message = """
همین حالا در راستین ثبت‌نام کن و شیبا هدیه بگیر.
فقط تا آخر هفته
"""


def alert_shib_prize_to_signup(token: str):
    return send_push_notif(
        token=token,
        title='تا ۲۰۰,۰۰۰ شیبا هدیه بگیرید',
        body=to_signup_message.strip(),
        image=settings.MINIO_STORAGE_STATIC_URL + '/ads/shiba-prize.png',
        link='https://raastin.com/auth/register?rewards=true&utm_source=push&utm_medium=push&utm_campaign=signup'
    )


def alert_new_coin_message(me: bool = False):
    return send_push_to_all(
        title='بیبی دوج را آنی خریداری کنید',
        body='از امروز می‌توانید کوین بیبی دوج را در راستین معامله کنید 🤩🤩🤩',
        image='https://api.raastin.com/static/ads/babydoge.jpg',
        link='https://raastin.com/wallet/spot/fast-buy?coin=1M-BABYDOGE&utm_source=push-retention&utm_campaign=coin&utm_term=babydoge',
        me=me
    )


def alert_margin_message():
    return send_push_to_all(
        title='معاملات تعهدی راستین',
        body='با معاملات تعهدی راستین حتی در بازار نزولی سود کنید 🤩🤩🤩',
        image='https://api.raastin.com/static/ads/margin.jpg',
        link='https://raastin.com/wallet/margin?&utm_source=push-retention&utm_campaign=margin&utm_term=margin'
    )


def send_push_to_all(title, body, image, link, me: bool = False):
    from accounts.models import FirebaseToken

    tokens = FirebaseToken.objects.all().order_by('id')

    if me:
        tokens = tokens.filter(user_id=1)

    for f in tokens:
        print('sending to token: %s' % f.id)
        send_push_notif(token=f.token, title=title, body=body, image=image, link=link)


to_trade_message = """
همین حالا در راستین معامله کن و شیبا هدیه بگیر.
فقط تا آخر هفته
"""



def alert_shib_prize_to_engagement(user: User):
    IMAGE_200K_SHIB = settings.MINIO_STORAGE_STATIC_URL + '/ads/shiba-prize.png'

    return send_push_notif_to_user(
        user=user,
        title='تا ۲۰۰,۰۰۰ شیبا هدیه بگیرید',
        body=to_trade_message.strip(),
        image=IMAGE_200K_SHIB,
        link='https://raastin.com/trade/market/BTCIRT?utm_source=push&utm_medium=push&utm_campaign=trade'
    )
