from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.models import FirebaseToken, User, ExternalNotification
from accounts.tasks import send_message_by_kavenegar
from accounts.utils.push_notif import send_push_notif, IMAGE_200K_SHIB
from ledger.models import Prize


@shared_task(queue='celery')
def retention_leads_to_signup():
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


def trigger_token(token: FirebaseToken):
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


@shared_task(queue='celery')
def retention_leads_to_upgrade_level():
    user_level_1 = User.objects.filter(
        is_active=True,
        level=User.LEVEL1
    )

    user_not_deposit = User.objects.filter(
        is_active=True,
        first_fiat_deposit_date=None,
        level__gte=User.LEVEL2
    )

    user_not_trade = User.objects.filter(
        is_active=True,
        level__gte=User.LEVEL2,
        first_fiat_deposit_date__isnull=False,
        account__trade_volume_irt__lt=Prize.TRADE_THRESHOLD_STEP1,
    )

    user_2h_level_1 = user_level_1.filter(
        date_joined__lt=timezone.now() - timedelta(hours=2),
        date_joined__gt=timezone.now() - timedelta(days=1)

    )
    user_1d_level_1 = user_level_1.filter(
        date_joined__lt=timezone.now() - timedelta(days=1),
        date_joined__gt=timezone.now() - timedelta(days=7)
    )
    user_7d_level_1 = user_level_1.filter(
        date_joined__lt=timezone.now() - timedelta(days=7)
    )

    user_12h_deposit = user_not_deposit.filter(
        date_joined__lt=timezone.now() - timedelta(hours=12),
        date_joined__gt=timezone.now() - timedelta(days=2)
    )
    user_2d_deposit = user_not_deposit.filter(
        date_joined__lt=timezone.now() - timedelta(days=2),
        date_joined__gt=timezone.now() - timedelta(days=4)
    )
    user_4d_deposit = user_not_deposit.filter(
        date_joined__lt=timezone.now() - timedelta(days=4),
        date_joined__gt=timezone.now() - timedelta(days=10)
    )
    user_10d_deposit = user_not_deposit.filter(
        date_joined__lt=timezone.now() - timedelta(days=10)
    )

    user_1d_trade = user_not_trade.filter(
        ate_joined__lt=timezone.now() - timedelta(days=3),
        date_joined__gt=timezone.now() - timedelta(days=10)
    )
    user_3d_trade = user_not_trade.filter(
        date_joined__lt=timezone.now() - timedelta(days=10),
        date_joined__gt=timezone.now() - timedelta(days=25)
    )
    user_7d_trade = user_not_trade.filter(
        date_joined__lt=timezone.now() - timedelta(days=25),
    )

    def check_condition_and_send_sms(user: User, scope: str):
        template = {
            ExternalNotification.SCOPE_TRIGGER_UPGRADE_LEVEL_FIRST: 'trigger_upgrade_level-first',
            ExternalNotification.SCOPE_TRIGGER_UPGRADE_LEVEL_SECOND: 'trigger_upgrade_level_second',
            ExternalNotification.SCOPE_TRIGGER_UPGRADE_LEVEL_THIRD: 'trigger_upgrade_level_third',

            ExternalNotification.SCOPE_TRIGGER_DEPOSIT_FIRST: 'trigger_deposit_first',
            ExternalNotification.SCOPE_TRIGGER_DEPOSIT_SECOND: 'trigger_deposit_second',
            ExternalNotification.SCOPE_TRIGGER_DEPOSIT_THIRD: 'trigger_deposit_third',
            ExternalNotification.SCOPE_TRIGGER_DEPOSIT_FOURTH: 'trigger_deposit_fourth',

            ExternalNotification.SCOPE_TRIGGER_TRADE_FIRST: 'trigger_trade_first',
            ExternalNotification.SCOPE_TRIGGER_TRADE_SECOND: 'trigger_trade_second',
            ExternalNotification.SCOPE_TRIGGER_TRADE_THIRD: 'trigger_trade_third',
        }

        if not ExternalNotification.objects.filter(user=user, scope=scope):
            ExternalNotification.send_sms(
                user=user,
                scope=template[scope],
                )
            ExternalNotification.objects.create(
                phone=user.phone,
                scope=scope,
                user=user
            )

    for user in user_2h_level_1:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_UPGRADE_LEVEL_FIRST)
    for user in user_1d_level_1:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_UPGRADE_LEVEL_SECOND)
    for user in user_7d_level_1:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_UPGRADE_LEVEL_THIRD)


    for user in user_12h_deposit:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_DEPOSIT_FIRST)
    for user in user_2d_deposit:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_DEPOSIT_SECOND)
    for user in user_4d_deposit:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_DEPOSIT_THIRD)
    for user in user_10d_deposit:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_DEPOSIT_FOURTH)

    for user in user_1d_trade:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_TRADE_FIRST)
    for user in user_3d_trade:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_TRADE_SECOND)
    for user in user_7d_trade:
        check_condition_and_send_sms(user, ExternalNotification.SCOPE_TRIGGER_TRADE_THIRD)

