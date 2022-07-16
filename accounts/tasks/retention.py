from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.utils.push_notif import send_push_notif, IMAGE_200K_SHIB


@shared_task(queue='celery')
def retention_leads_to_signup():
    from accounts.models import FirebaseToken

    tokens = FirebaseToken.objects.filter(user=None)

    token_state_1 = tokens.filter(
        state=FirebaseToken.STATE_1,
        created__lt=timezone.now()-timedelta(hours=2),
        created__gt=timezone.now() - timedelta(days=1),
    )

    for token in token_state_1:
        resp = trigger_token(token)
        if resp:
            token.state = FirebaseToken.STATE_2
            token.save()

    token_state_2 = tokens.filter(
        state=FirebaseToken.STATE_2,
        created__lt=timezone.now() - timedelta(days=1),
        created__gt=timezone.now() - timedelta(days=7)
    )
    for token in token_state_2:
        resp = trigger_token(token)
        if resp:
            token.state = FirebaseToken.STATE_3
            token.save()

    token_state_3 = tokens.filter(
        state=FirebaseToken.STATE_3,
        created__lt=timezone.now() - timedelta(days=7)
    )
    for token in token_state_3:
        resp = trigger_token(token)
        if resp:
            token.state = FirebaseToken.STATE_4
            token.save()


def trigger_token(token):
    from accounts.models import FirebaseToken

    templates = {
        FirebaseToken.STATE_1: {
            'title': 'همین الان در راستین ثبت‌نام کن!',
            'body': 'در راستین ثبت‌نام کنید و تا 200 هزار شیبا هدیه رایگان بگیرید.',
            'image': IMAGE_200K_SHIB,
            'link': 'https://raastin.com/auth/register?rewards=true&utm_source=push&utm_medium=retention&utm_campaign=signup&utm_term=new1',
        },
        FirebaseToken.STATE_2: {
            'title': 'در راستین ثبت‌نام کن و تا 200 هزار شیبا هدیه بگیر.',
            'body': 'اگر تا آخر هفته در راستین ثبت‌نام کنید تا 200 هزار شیبا هدیه رایگان می‌گیرید.',
            'image': IMAGE_200K_SHIB,
            'link': 'https://raastin.com/auth/register?rewards=true&utm_source=push&utm_medium=retention&utm_campaign=signup&utm_term=new2',
        },
        FirebaseToken.STATE_3: {
            'title': 'آخرین فرصت دریافت 200 هزار شیبا در راستین',
            'body': 'در راستین ثبت‌نام کنید و تا 200 هزار شیبا هدیه رایگان بگیرید.',
            'image': IMAGE_200K_SHIB,
            'link': 'https://raastin.com/auth/register?rewards=true&utm_source=push&utm_medium=retention&utm_campaign=signup&utm_term=new3',
        },
    }
    data = templates[token.state]
    return send_push_notif(
        token=token.token,
        title=data['title'],
        body=data['body'],
        image=data['image'],
        link=data['link'],
    )
