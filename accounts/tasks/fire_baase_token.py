from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.models import FirebaseToken
from accounts.utils.push_notif import trigger_token_level_1, trigger_token_level_2, trigger_token_level_3


@shared_task(queue='sms')
def change_token_state_and_send_push():
    tokens = FirebaseToken.objects.filter(user=None)

    token_state_1 = tokens.filter(
        state=FirebaseToken.STATE_1,
        created__lt=timezone.now()-timedelta(hours=2),
        created__gt=timezone.now() - timedelta(days=1),
    )

    for token in token_state_1:
        trigger_token_level_1(token.token)
        token.state = FirebaseToken.STATE_2
        token.save()

    token_state_2 = tokens.filter(
        state=FirebaseToken.STATE_2,
        created__gt=timezone.now() - timedelta(hours=7),
        created__lt=timezone.now() - timedelta(days=1)
    )
    for token in token_state_2:
        trigger_token_level_2(token.token)
        token.state = FirebaseToken.STATE_3
        token.save()

    token_state_3 = tokens.filter(
        state=FirebaseToken.STATE_3,
        created__lt=timezone.now() - timedelta(days=7)
    )
    for token in token_state_3:
        trigger_token_level_3(token.token)
        token.state = FirebaseToken.STATE_4
        token.save()
