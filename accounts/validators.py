import re

from django.core.exceptions import ValidationError


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


def password_validator(value):
    if not len(value) >= 6:
        raise ValidationError('گذرواژه باید حداقل ۶ حرف باشد.')
