import logging
from typing import Union

from accounts.models import User
from accounts.utils.admin import url_to_edit_object
from accounts.utils.similarity import name_similarity
from accounts.utils.telegram import send_support_message
from accounts.verifiers.finotech import ServerError
from accounts.verifiers.jibit import JibitRequester
from financial.models import BankCard, BankAccount

logger = logging.getLogger(__name__)


def basic_verify(user: User):
    if user.level != User.LEVEL1:
        logger.info('ignoring double verifying user_d = %d' % user.id)
        return

    bank_card = user.kyc_bank_card

    if not bank_card:
        logger.info('ignoring verify level2 due to no bank_account for user_d = %d' % user.id)
        return

    if not user.national_code_verified or not user.birth_date_verified or not bank_card.verified:
        logger.info('verifying national_code, birth_date, bank_card for user_d = %d' % user.id)

        if not verify_bank_card_by_national_code(bank_card):
            return

    if bank_card.verified and (not user.first_name_verified or not user.last_name_verified):
        logger.info('verifying name, bank_card for user_d = %d' % user.id)

        if not verify_name_by_bank_card(bank_card):
            return

    user.verify_level2_if_not()


def shahkar_check(user: User, phone: str, national_code: str) -> Union[bool, None]:
    requester = JibitRequester(user)
    resp = requester.matching(phone_number=phone, national_code=national_code)

    if resp.success:
        return resp.data['matched']
    elif resp.data['code'] in ['mobileNumber.not_valid', 'nationalCode.not_valid']:
        return False
    else:
        logger.warning('JIBIT shahkar not succeeded', extra={
            'user': user,
            'resp': resp.data,
            'phone': phone,
            'national_code': national_code
        })
        return


def update_bank_card_info(bank_card: BankCard, data: dict):
    info = data['cardInfo']
    bank_card.bank = info['bank']
    bank_card.type = info['type']
    bank_card.owner_name = info['ownerName']
    bank_card.deposit_number = info['depositNumber']
    bank_card.save()


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
            logger.error('JIBIT timeout verify_national_code')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_national_code_with_phone(user, retry - 1)

    user.national_code_phone_verified = verified
    user.save()

    return verified


def verify_bank_card_by_national_code(bank_card: BankCard, retry: int = 2) -> Union[bool, None]:
    user = bank_card.user

    if user.national_code_verified and user.birth_date_verified and bank_card.verified:
        return True

    if not user.national_code or not bank_card or not user.birth_date:
        return False

    if BankCard.live_objects.filter(card_pan=bank_card.card_pan, verified=True).exclude(id=bank_card.id).exists():
        logger.info('rejecting bank card because of duplication')
        bank_card.reject_reason = BankCard.DUPLICATED
        bank_card.verified = False
        bank_card.save()
        user.change_status(User.REJECTED)
        return False

    requester = JibitRequester(user)

    try:
        resp = requester.matching(
            national_code=user.national_code,
            birth_date=user.birth_date,
            card_pan=bank_card.card_pan
        )

        if resp.success:
            card_matched = resp.data['matched']
            identity_matched = None

            if card_matched:
                identity_matched = True

        elif resp.data['code'].startswith('card.') and resp.data['code'] != 'card.provider_is_not_active':
            card_matched = False
            identity_matched = None
        elif resp.data['code'] in ('identity_info.not_found', 'nationalCode.not_valid', 'matching.unknown'):
            identity_matched = False
            card_matched = None
        else:
            logger.warning('JIBIT card <-> national_code not succeeded', extra={
                'user': user,
                'resp': resp.data['code'],
                'card': bank_card,
            })
            return

    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('JIBIT timeout user_primary_info')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_bank_card_by_national_code(bank_card, retry - 1)

    user.national_code_verified = identity_matched
    user.birth_date_verified = identity_matched
    user.save(update_fields=['national_code_verified', 'birth_date_verified'])

    bank_card.verified = card_matched
    bank_card.save(update_fields=['verified'])

    if identity_matched is False or card_matched is False:
        user.change_status(User.REJECTED)
        return False
    else:
        user.verify_level2_if_not()
        return True


def verify_name_by_bank_card(bank_card: BankCard, retry: int = 2) -> Union[bool, None]:
    if not bank_card.kyc:
        return False

    requester = JibitRequester(bank_card.user)

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

        elif resp.data['code'].startswith('card.') and resp.data['code'] != 'card.provider_is_not_active':
            bank_card.verified = False
            bank_card.reject_reason = resp.data['code']
            bank_card.save()

            bank_card.user.change_status(User.REJECTED)

            return False
        else:
            logger.warning('JIBIT card verification not succeeded', extra={
                'bank_card': bank_card,
                'resp': resp.data['code'],
            })
            return

    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('JIBIT timeout bank_card')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_name_by_bank_card(bank_card, retry - 1)


def verify_bank_card(bank_card: BankCard, retry: int = 2) -> Union[bool, None]:
    if bank_card.verified:
        return

    if BankCard.live_objects.filter(card_pan=bank_card.card_pan, verified=True).exclude(id=bank_card.id).exists():
        logger.info('rejecting bank card because of duplication')
        bank_card.reject_reason = BankCard.DUPLICATED
        bank_card.verified = False
        bank_card.save()
        return False

    requester = JibitRequester(bank_card.user)

    try:
        resp = requester.get_card_info(card_pan=bank_card.card_pan)

        if resp.success:
            update_bank_card_info(bank_card, resp.data)

            verified = name_similarity(bank_card.user.get_full_name(), bank_card.owner_name)

            bank_card.verified = verified

            if not verified:
                bank_card.reject_reason = 'name.mismatch'

            bank_card.save()
                
            return verified
        
        elif resp.data['code'].startswith('card.') and resp.data['code'] != 'card.provider_is_not_active':
            bank_card.verified = False
            bank_card.reject_reason = resp.data['code']
            bank_card.save()

            return False
        else:
            logger.warning('JIBIT card verification not succeeded', extra={
                'bank_card': bank_card,
                'resp': resp.data['code'],
            })
            return
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('JIBIT timeout bank_card')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_bank_card(bank_card, retry - 1)


DEPOSIT_STATUS_MAP = {
    'ACTIVE': BankAccount.ACTIVE,
    'BLOCK_WITH_DEPOSIT': BankAccount.DEPOSITABLE_SUSPENDED,
    'BLOCK_WITHOUT_DEPOSIT': BankAccount.NON_DEPOSITABLE_SUSPENDED,
    'IDLE': BankAccount.STAGNANT,
    'UNKNOWN': BankAccount.UNKNOWN,
}


def verify_bank_account(bank_account: BankAccount, retry: int = 2) -> Union[bool, None]:
    if BankAccount.live_objects.filter(iban=bank_account.iban, verified=True).exclude(id=bank_account.id).exists():
        logger.info('rejecting bank account because of duplication')
        bank_account.verified = False
        bank_account.save()
        return False

    requester = JibitRequester(bank_account.user)

    try:
        iban_info = requester.get_iban_info(bank_account.iban)
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('JIBIT timeout bank_account')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_bank_account(bank_account, retry - 1)

    if not iban_info.success:
        if iban_info.data['code'] == 'iban.not_valid':
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

    iban_info = iban_info.data['ibanInfo']

    bank_account.bank = iban_info['bank']
    bank_account.deposit_address = iban_info['depositNumber']
    bank_account.card_pan = ''
    bank_account.deposit_status = DEPOSIT_STATUS_MAP.get(iban_info['status'], '')

    owners = bank_account.owners = iban_info['owners']

    user = bank_account.user

    verified = False

    if len(owners) >= 1:
        owner = owners[0]
        owner_full_name = owner['firstName'] + ' ' + owner['lastName']

        verified = name_similarity(owner_full_name, user.get_full_name())

    bank_account.verified = verified
    bank_account.save()

    return verified
