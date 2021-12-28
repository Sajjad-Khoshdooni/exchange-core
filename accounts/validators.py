import re

from django.core.exceptions import ValidationError


def mobile_number_validator(value):
    if not re.match(r'^((09\d{9})|(00\d{8,15}))$', value):
        raise ValidationError('شماره موبایل معتبر نیست.')


def iran_mobile_number_validator(value):
    if not re.match(r'(09)(\d){9}', value):
        raise ValidationError('شماره موبایل برای ایران معتبر نیست.')


def password_validator(value):
    if not len(value) >= 6:
        raise ValidationError('گذرواژه باید حداقل ۶ حرف باشد.')
