from django.db.models import Sum

from financial.models import FiatWithdrawRequest, Payment
from ledger.utils.fields import CANCELED


def auto_verify(withdraw: FiatWithdrawRequest):
    user = withdraw.bank_account.user

    total_deposits = Payment.objects.filter(
        bank_card__user=user
    ).exclude(status=CANCELED).aggregate(amount=Sum('amount'))['amount'] or 0

    total_withdraws = FiatWithdrawRequest.objects.filter(
        bank_account__user=user
    ).exclude(status=FiatWithdrawRequest.CANCELED).aggregate(amount=Sum('amount'))['amount'] or 0

    return total_withdraws <= 1.2 * total_deposits
