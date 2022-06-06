from collections import defaultdict
from decimal import Decimal

from django.db.models import Q

from accounts.models import Account
from ledger.models import Trx, Wallet
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
