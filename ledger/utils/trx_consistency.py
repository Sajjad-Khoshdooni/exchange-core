from collections import defaultdict
from decimal import Decimal

from django.db.models import Q, Sum

from accounts.models import Account
from ledger.models import Trx, Wallet, BalanceLock
import logging

logger = logging.getLogger(__name__)


def check_wallet_balance_correctness(wallet: Wallet, balance: Decimal):
    if wallet.market != Wallet.LOAN:
        valid = balance >= 0
    else:
        valid = balance <= 0

    if not valid:
        logger.info('Invalid wallet state for wallet_id=%s, balance=%s' % (wallet.id, balance))

    return valid


def check_account_consistency(account: Account):
    if not account.is_ordinary_user():
        logger.info('ignoring non ordinary account checking! account_id=%s' % account.id)
        return

    trx_history = Trx.objects.filter(Q(sender__account=account) | Q(receiver__account=account)).order_by('created')

    balances = defaultdict(Decimal)

    for trx in trx_history:
        if trx.sender.account == account:
            balances[trx.sender_id] -= trx.amount
            if not check_wallet_balance_correctness(trx.sender, balances[trx.sender_id]):
                logger.info('trx_id= %s, created= %s' % (trx.id, trx.created))
                balances[trx.sender_id] = 0

        if trx.receiver.account == account:
            balances[trx.receiver_id] += trx.amount
            if not check_wallet_balance_correctness(trx.receiver, balances[trx.receiver_id]):
                logger.info('trx_id= %s, created= %s' % (trx.id, trx.created))
                balances[trx.receiver_id] = 0


def check_all_accounts_consistency():
    for account in Account.objects.filter(type=Account.ORDINARY):
        check_account_consistency(account)


def check_overall_consistency():
    received = Trx.objects.values('receiver', 'receiver__market').annotate(amount=Sum('amount'))
    sent = Trx.objects.values('sender', 'sender__market').annotate(amount=Sum('amount'))

    received_dict = {}
    sent_dict = {}

    for r in received:
        received_dict[(r['receiver'], r['receiver__market'])] = r['amount']

    for s in sent:
        sent_dict[(s['sender'], s['sender__market'])] = s['amount']

    locked = BalanceLock.objects.filter(freed=False).values('wallet', 'wallet__market').annotate(amount=Sum('amount'))
    locked_dict = {}

    for l in locked:
        locked_dict[(l['wallet'], l['wallet__market'])] = l['amount']

    for w in Wallet.objects.all().prefetch_related('account'):
        key = (w.id, w.market)
        balance = received_dict.get(key, 0) - sent_dict.get(key, 0)
        locked = locked_dict.get(key, 0)
        check_balance = w.account.type is None

        if check_balance:
            if balance < 0:
                logger.info("%s (%s): negative balance (%f)" % (w, w.id, balance))

            if locked > balance:
                logger.info("%s (%s): locked (%f) > balance (%f)" % (w, w.id, locked, balance))
