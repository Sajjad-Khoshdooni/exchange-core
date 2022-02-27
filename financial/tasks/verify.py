from celery import shared_task

from accounts.verifiers.basic_verify import verify_bank_card, verify_bank_account
from financial.models import BankCard, BankAccount
import logging

logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def verify_bank_card_task(bank_card_id: int):
    bank_card = BankCard.objects.get(id=bank_card_id)  # type: BankCard

    verified = verify_bank_card(bank_card)

    logger.info('bank card %d verified %s' % (bank_card_id, verified))


@shared_task(queue='celery')
def verify_bank_account_task(bank_account_id: int):
    bank_account = BankAccount.objects.get(id=bank_account_id)  # type: BankAccount

    verified = verify_bank_account(bank_account)

    logger.info('bank account %d verified %s' % (bank_account_id, verified))
