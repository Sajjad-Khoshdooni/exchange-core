from django.db.models import Sum

from ledger.models import Trx, Asset


def get_user_type_balance(user_type: str, asset: Asset = None):

    receiver_kwargs = {
        'receiver__account__type': user_type,
    }

    sender_kwargs = {
        'sender__account__type': user_type,
    }

    if asset:
        sender_kwargs['sender__asset'] = receiver_kwargs['receiver__asset'] = asset

    received = Trx.objects.filter(**receiver_kwargs).aggregate(amount=Sum('amount'))['amount'] or 0
    sent = Trx.objects.filter(**sender_kwargs).aggregate(amount=Sum('amount'))['amount'] or 0

    return received - sent
