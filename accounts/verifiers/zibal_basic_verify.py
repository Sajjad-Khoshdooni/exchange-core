import logging
from typing import Union

from accounts.models import User
from accounts.utils.admin import url_to_edit_object
from accounts.utils.similarity import name_similarity
from accounts.utils.telegram import send_support_message
from accounts.verifiers.jibit_basic_verify import send_shahkar_rejection_message, update_bank_card_info, ServerError
from accounts.verifiers.zibal import ZibalRequester
from financial.models import BankCard, BankAccount

logger = logging.getLogger(__name__)


def shahkar_check(user: User, phone: str, national_code: str) -> Union[bool, None]:
    requester = ZibalRequester(user)
    resp = requester.matching(phone_number=phone, national_code=national_code)
    resp_data = resp.data
    if resp.success:
        is_matched = resp_data['data']['matched']
        if not is_matched:
            send_shahkar_rejection_message(user, resp)
        return is_matched
    else:
        logger.warning('Zibal shahkar not succeeded', extra={
            'user': user,
            'resp': resp_data,
            'phone': phone,
            'national_code': national_code
        })
        return


def verify_name_by_bank_card(bank_card: BankCard, retry: int = 2) -> Union[bool, None]:
    if not bank_card.kyc:
        return False

    requester = ZibalRequester(bank_card.user)

    user = bank_card.user

    if user.first_name_verified and user.last_name_verified:
        return True

    try:
        resp = requester.get_card_info(card_pan=bank_card.card_pan)

        if resp.success:
            update_bank_card_info(bank_card, resp.data)
            verified = name_similarity(bank_card.user.get_full_name(), bank_card.owner_name)

            if verified:
                user.first_name_verified = True
                user.last_name_verified = True
                user.save(update_fields=['first_name_verified', 'last_name_verified'])

                user.verify_level2_if_not()
                return True
            else:
                link = url_to_edit_object(user)
                send_support_message(
                    message='اطلاعات نام کاربر مورد تایید قرار نگرفت. لطفا دستی بررسی شود.',
                    link=link
                )
                return
        else:
            bank_card.verified = False
            bank_card.reject_reason = resp.data['message']
            bank_card.save()

            bank_card.user.change_status(User.REJECTED)

            logger.warning('Zibal card verification not succeeded', extra={
                'bank_card': bank_card,
                'resp': resp.data['message'],
            })
            return False

    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('Zibal timeout bank_card')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_name_by_bank_card(bank_card, retry - 1)


def verify_bank_account(bank_account: BankAccount, retry: int = 2) -> Union[bool, None]:
    if BankAccount.live_objects.filter(iban=bank_account.iban, verified=True).exclude(id=bank_account.id).exists():
        logger.info('rejecting bank account because of duplication')
        bank_account.verified = False
        bank_account.save()
        return False

    requester = ZibalRequester(bank_account.user)

    try:
        iban_info = requester.get_iban_info(bank_account.iban)
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('Zibal timeout bank_account')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_bank_account(bank_account, retry - 1)

    if not iban_info.success:
        if iban_info.data['result'] == 21:
            bank_account.verified = False
            bank_account.save()
            return False

        else:
            link = url_to_edit_object(bank_account)
            send_support_message(
                message='تایید شماره شبای کاربر با مشکل مواجه شد. لطفا دستی بررسی شود.',
                link=link
            )
            return

    iban_info = iban_info.data['data']

    bank_account.bank = iban_info['bankName']
    bank_account.card_pan = ''
    owners = bank_account.owners = iban_info['name']
    user = bank_account.user

    verified = False

    if len(owners) >= 1:
        owner = owners[0]
        verified = name_similarity(owner, user.get_full_name())

    bank_account.verified = verified
    bank_account.save()

    return verified


def verify_national_code_with_phone(user: User, retry: int = 2) -> Union[bool, None]:
    if user.level != User.LEVEL2:
        return False

    if not user.national_code:
        return False

    try:
        verified = shahkar_check(user, user.phone, user.national_code)

        if verified is None:
            return

    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('Zibal timeout verify_national_code')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_national_code_with_phone(user, retry - 1)

    user.national_code_phone_verified = verified
    user.save(update_fields=['national_code_phone_verified'])

    return verified
