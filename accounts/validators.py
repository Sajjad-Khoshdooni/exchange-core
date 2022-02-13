import re

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password


class RegexValidator:
    def __init__(self, pattern: str):
        self.pattern = pattern

    def __call__(self, value):
        if not re.match(self.pattern, value):
            raise ValidationError('یک مقدار معتبر وارد کنید.')


def mobile_number_validator(value):
    if not re.match(r'^((09\d{9})|(00\d{8,15}))$', value):
        raise ValidationError('شماره موبایل معتبر نیست.')


def iran_mobile_number_validator(value):
    if not re.match(r'(09)(\d){9}', value):
        raise ValidationError('شماره موبایل برای ایران معتبر نیست.')


def national_card_code_validator(value):

    if type(value) is str and 8 <= len(value) < 10:
        value = (10 - len(value)) * '0' + value

    if not re.match(r'^[0-9]{10}$', value):
        raise ValidationError('کد ملی باید 10 رقمی باشد.')

    array = list(map(int, value))

    _sum = 0
    for i in range(9):
        _sum += (10 - i) * array[i]

    control = _sum % 11

    if control >= 2:
        control = 11 - control

    if control != array[9]:
        raise ValidationError('کد ملی معتبر نیست.')


def password_validator(password: str, user=None):
    errors = []
    try:
        validate_password(password=password, user=user)
    except ValidationError as e:
        errors.extend(e.messages)

    if errors:
        raise ValidationError(errors)


def iban_validator(value: str):
    if not re.match(r'^IR[0-9]{24}$', value):
        raise ValidationError('شماره شبا نامعتبر است.')

    value = value[4:] + value[:4]
    value = value.replace('I', '18').replace('R', '27')

    if int(value) % 97 != 1:
        raise ValidationError('شماره شبا نامعتبر است.')


def bank_card_pan_validator(value: str):
    if not re.match(r'^[0-9]{16}$', value):
        raise ValidationError('شماره کارت نامعتبر است.')

    _sum = 0

    array = list(map(int, value))

    for index, digit in enumerate(array):
        s = (2 - (index % 2)) * digit
        if s > 9:
            s -= 9
        _sum += s

    if _sum % 10 != 0:
        raise ValidationError('شماره شبا نامعتبر است.')
