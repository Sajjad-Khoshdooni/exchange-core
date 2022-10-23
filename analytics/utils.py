from django.db.models import Sum

from accounts.models import User
from financial.models import Payment
from ledger.models import Transfer
from ledger.utils.fields import DONE
from market.models import Trade


def produce_users_analytics(user_ids: list):
    users = User.objects.filter(id__in=user_ids)
    payments = Payment.objects.filter(
        payment_request__bank_card__user_id__in=user_ids,
        status=DONE
    )
    transfers = Transfer.objects.filter(wallet__account__user_id__in=users)

    with_deposit_users = set(payments.values_list('payment_request__bank_card__user_id', flat=True))
    with_deposit_users |= set(transfers.values_list('wallet__account__user_id', flat=True))

    crypto_deposit_volume = transfers.aggregate(value=Sum('irt_value'))['value'] or 0
    fiat_deposit_volume = payments.aggregate(value=Sum('payment_request__amount'))['value'] or 0

    trades = Trade.objects.filter(order__wallet__account__user_id__in=users)

    return {
        'users': len(user_ids),
        'verified': users.filter(level__gt=User.LEVEL1).count(),
        'deposited': with_deposit_users,
        'deposit_value': fiat_deposit_volume + crypto_deposit_volume,
        'traders': len(set(trades.values_list('order__wallet__account__user_id', flat=True))),
        'trade_volume': trades.aggregate(value=Sum('irt_value'))['value'] or 0,
    }