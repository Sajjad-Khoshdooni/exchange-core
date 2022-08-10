import logging

from accounts.models import User
from accounts.utils.admin import url_to_edit_object
from accounts.utils.similarity import str_similar_rate, clean_persian_name, rotate_words
from accounts.utils.telegram import send_support_message
from accounts.verifiers.finotech import ServerError
from accounts.verifiers.jibit import JibitRequester
from financial.models import BankCard, BankAccount

logger = logging.getLogger(__name__)


IBAN_NAME_SIMILARITY_THRESHOLD = 0.75


def basic_verify(user: User):
    if user.level != User.LEVEL1:
        logger.info('ignoring double verifying user_d = %d' % user.id)
        return

    queryset = user.bankcard_set.all()
    bank_card = queryset.filter(verified=True).first() or queryset.filter(verified=None).first() or \
                queryset.filter(verified=False).first()

    if not bank_card:
        logger.info('ignoring verify level2 due to no bank_account for user_d = %d' % user.id)
        return

    if not user.national_code_verified or not user.birth_date_verified or not bank_card.verified:
        logger.info('verifying national_code, birth_date, bank_card for user_d = %d' % user.id)

        if not verify_bank_card_by_national_code(bank_card):
            return

    if bank_card.verified and (not user.first_name_verified or not user.last_name_verified):
        logger.info('verifying name, bank_card for user_d = %d' % user.id)

        if not verify_bank_card_by_name(bank_card):
            return

    user.verify_level2_if_not()


def verify_national_code_with_phone(user: User, retry: int = 2) -> bool:
    if user.level != User.LEVEL2:
        return False

    if not user.national_code:
        return False

    requester = JibitRequester(user)

    try:
        verified = requester.matching(phone_number=user.phone, national_code=user.national_code)
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('jibit timeout verify_national_code')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_national_code_with_phone(user, retry - 1)

    if not verified:
        user.change_status(User.REJECTED)
    else:
        user.change_status(User.VERIFIED)

    return verified


def verify_bank_card_by_national_code(bank_card: BankCard, retry: int = 2) -> bool:
    user = bank_card.user

    if user.birth_date_verified and user.bankcard_set.filter(verified=True):
        return True

    if not user.national_code or not bank_card or not user.birth_date:
        return False

    requester = JibitRequester(user)

    try:
        matched = requester.matching(
            national_code=user.national_code,
            birth_date=user.birth_date,
            card_pan=bank_card.card_pan
        )
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('jibit timeout user_primary_info')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_bank_card_by_national_code(bank_card, retry - 1)

    user.birth_date_verified = matched
    user.save(update_fields=['birth_date_verified'])

    bank_card.verified = matched
    bank_card.save(update_fields=['verified'])

    if not matched:
        user.change_status(User.REJECTED)
        return False

    user.verify_level2_if_not()

    return True


def verify_bank_card_by_name(bank_card: BankCard, retry: int = 2) -> bool:
    requester = JibitRequester(bank_card.user)

    if not bank_card.verified:
        return

    user = bank_card.user

    if user.first_name_verified and user.last_name_verified:
        return True

    try:
        matched = requester.matching(card_pan=bank_card.card_pan, full_name=bank_card.user.get_full_name())
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('jibit timeout bank_card')
            return
        else:
            logger.info('Retrying verify_national_code...')
            return verify_bank_card_by_name(bank_card, retry - 1)

    user.first_name_verified = matched
    user.last_name_verified = matched
    user.save(update_fields=['first_name_verified', 'last_name_verified'])

    if not matched:
        user.change_status(User.REJECTED)
        return False

    user.verify_level2_if_not()

    return True


DEPOSIT_STATUS_MAP = {
    'ACTIVE': BankAccount.ACTIVE,
    'BLOCK_WITH_DEPOSIT': BankAccount.DEPOSITABLE_SUSPENDED,
    'BLOCK_WITHOUT_DEPOSIT': BankAccount.NON_DEPOSITABLE_SUSPENDED,
    'IDLE': BankAccount.STAGNANT,
    'UNKNOWN': BankAccount.UNKNOWN,
}


def verify_bank_account(bank_account: BankAccount, retry: int = 2) -> bool:
    requester = JibitRequester(bank_account.user)

    try:
        iban_info = requester.get_iban_info(bank_account.iban)
    except (TimeoutError, ServerError):
        if retry == 0:
            logger.error('jibit timeout bank_account')
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

    bank_account.bank_name = iban_info['bank']
    bank_account.deposit_address = iban_info['depositNumber']
    bank_account.card_pan = ''
    bank_account.deposit_status = DEPOSIT_STATUS_MAP.get(iban_info['status'], '')

    owners = bank_account.owners = iban_info['owners']

    user = bank_account.user

    verified = False

    if len(owners) >= 1:
        owner = owners[0]
        owner_full_name = owner['firstName'] + ' ' + owner['lastName']

        name1, name2 = clean_persian_name(owner_full_name), clean_persian_name(user.get_full_name())

        verified = str_similar_rate(name1, name2) >= IBAN_NAME_SIMILARITY_THRESHOLD

        if not verified:
            name1_rotate = rotate_words(name1)
            verified = str_similar_rate(name1_rotate, name2) >= IBAN_NAME_SIMILARITY_THRESHOLD

    bank_account.verified = verified
    bank_account.save()

    return verified
