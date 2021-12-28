import re


def is_phone(phone: str):
    return re.match(r'(09)(\d){9}', phone)


def is_email(email: str):
    return '@' in email
