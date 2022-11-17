from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from ledger.models import Transfer

MAX_DAILY_AUTO_VERIFY = 2_000_000


def auto_withdraw_verify(transfer: Transfer) -> Decimal:
    assert not transfer.deposit

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    withdraw_value = Transfer.objects.filter(
        deposit=False,
        wallet__account=transfer.wallet.account,
        created__gte=today
    ).aggregate(value=Sum('irt_value'))['value'] or 0

    return withdraw_value <= MAX_DAILY_AUTO_VERIFY
