import re

from django.core.exceptions import ValidationError


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
        raise ValidationError('شماره کارت نامعتبر است.')
