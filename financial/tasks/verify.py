from celery import shared_task

from accounts.models import Notification
from accounts.verifiers.basic_verify import verify_bank_card, verify_bank_account
from financial.models import BankCard, BankAccount
import logging

logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def verify_bank_card_task(bank_card_id: int):
    bank_card = BankCard.objects.get(id=bank_card_id)  # type: BankCard

    verified = verify_bank_card(bank_card)

    if verified:
        title = 'شماره کارت وارد شده تایید شد.'
        message = 'شماره کارت %s تایید شد.' % bank_card
        level = Notification.SUCCESS
    else:
        title = 'شماره کارت وارد شده تایید نشد.'
        message = 'شماره کارت %s متعلق به کد ملی ثبت شده نیست.' % bank_card
        level = Notification.ERROR

    Notification.send(
        recipient=bank_card.user,
        title=title,
        message=message,
        level=level
    )

    logger.info('bank card %d verified %s' % (bank_card_id, verified))


@shared_task(queue='celery')
def verify_bank_account_task(bank_account_id: int):
    bank_account = BankAccount.objects.get(id=bank_account_id)  # type: BankAccount

    verified = verify_bank_account(bank_account)

    if verified:
        title = 'شماره شبای وارد شده تایید شد.'
        message = 'شماره شبای %s تایید شد.' % bank_account
        level = Notification.SUCCESS
    else:
        title = 'شماره شبای وارد شده تایید نشد.'
        message = 'شماره شبای %s متعلق به شما نیست.' % bank_account
        level = Notification.ERROR

    Notification.send(
        recipient=bank_account.user,
        title=title,
        message=message,
        level=level
    )

    logger.info('bank account %d verified %s' % (bank_account_id, verified))