import logging
import time
from datetime import timedelta

from celery import shared_task
from django.db.models import Avg, Count
from django.utils import timezone

from accounts.models import User, ExternalNotification
from accounts.utils.push_notif import send_push_notif, IMAGE_200K_SHIB
from ledger.models import Asset

logger = logging.getLogger(__name__)


@shared_task(queue='retention')
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


@shared_task(queue='retention')
def retention_actions():
    user_level_1 = User.objects.filter(
        is_active=True,
        level=User.LEVEL1,
    ).exclude(verify_status=User.PENDING)

    user_not_deposit = User.objects.filter(
        is_active=True,
        first_fiat_deposit_date=None,
        level__gte=User.LEVEL2
    )

    user_not_trade = User.objects.filter(
        is_active=True,
        level__gte=User.LEVEL2,
        first_fiat_deposit_date__isnull=False,
        account__trade_volume_irt__lt=2_000_000,
    )

    now = timezone.now()

    def before(hours: int = 0, days: int = 0):
        return now - timedelta(days=days, hours=hours)

    candidate = {
        ExternalNotification.SCOPE_VERIFY1: user_level_1.filter(date_joined__range=(before(days=1), before(hours=3))),
        ExternalNotification.SCOPE_VERIFY2: user_level_1.filter(date_joined__range=(before(days=2), before(days=1))),
        ExternalNotification.SCOPE_VERIFY3: user_level_1.filter(date_joined__range=(before(days=10), before(days=3))),

        ExternalNotification.SCOPE_DEPOSIT1: user_not_deposit.filter(date_joined__range=(before(days=2), before(hours=12))),
        ExternalNotification.SCOPE_DEPOSIT2: user_not_deposit.filter(date_joined__range=(before(days=4), before(days=2))),
        ExternalNotification.SCOPE_DEPOSIT3: user_not_deposit.filter(date_joined__range=(before(days=8), before(days=5))),
        ExternalNotification.SCOPE_DEPOSIT4: user_not_deposit.filter(date_joined__range=(before(days=30), before(days=10))),

        ExternalNotification.SCOPE_TRADE1: user_not_trade.filter(date_joined__range=(before(days=5), before(days=3))),
        ExternalNotification.SCOPE_TRADE2: user_not_trade.filter(date_joined__range=(before(days=18), before(days=9))),
        ExternalNotification.SCOPE_TRADE3: user_not_trade.filter(date_joined__range=(before(days=40), before(days=21))),
    }

    missed = 0

    for scope, users in candidate.items():
        sent_users = ExternalNotification.objects.filter(scope=scope).values_list('user_id', flat=True)
        users = users.exclude(id__in=sent_users)

        for user in users:
            sent = ExternalNotification.send_sms(
                user=user,
                scope=scope,
            )

            if not sent:
                missed += 1
            else:
                missed = 0

            if missed >= 3:
                logger.warning('sending retention ignored due to multiple sms.ir failures')
                return

            time.sleep(1)


@shared_task(queue='retention')
def retention_missing_users():

    all_symbols = list(Asset.objects.filter(enable=True).values_list('symbol', flat=True))

    top_gainers = CoinMarketCap.objects.filter(
        symbol__in=all_symbols,
        change_24h__gte=1
    ).order_by('-change_24h').values_list('change_24h', flat=True)[:10].aggregate(avg=Avg('change_24h'), count=Count('*'))

    avg_gain = round(top_gainers.get('avg', 0))
    count = top_gainers.get('count', 0)

    def params_converter(params):
        return {
            **params,
            'name': params['name'].format({
                'count': count,
                'percent': avg_gain
            })
        }

    if avg_gain >= 5 and count >= 5:
        recently_sent_users = ExternalNotification.objects.filter(
            created__gte=timezone.now() - timedelta(days=7)
        ).values_list('user', flat=True).distinct()

        users = User.objects.filter()

        for user in users:
            ExternalNotification.send_sms(user, ExternalNotification.SCOPE_TOP_GAINERS, params_converter)

