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


def password_validator(password: str, user=None):
    errors = []
    try:
        validate_password(password=password, user=user)
    except ValidationError as e:
        errors.extend(e.messages)

    if errors:
        raise ValidationError(errors)
