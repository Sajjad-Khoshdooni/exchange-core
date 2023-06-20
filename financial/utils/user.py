from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from financial.models import Payment
from ledger.utils.fields import DONE


def get_today_fiat_deposits(user: User):
    today = timezone.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

    return Payment.objects.filter(
        payment_request__bank_card__user=user,
        created__gte=today,
        status=DONE
    ).aggregate(
        total=Sum('payment_request__amount')
    )['total'] or 0
