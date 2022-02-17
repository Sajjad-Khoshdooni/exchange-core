from decimal import Decimal


def get_precision(amount: Decimal):
    amount = str(amount)

    if '.' in amount:
        amount = amount.rstrip('0').rstrip('.')

    if '.' not in amount:
        return len(amount.rstrip('0')) - len(amount)
    else:
        return len(amount.split('.')[1])


def decimal_to_str(amount: Decimal):
    amount = str(amount)
    if '.' in amount:
        amount = amount.rstrip('0').rstrip('.')
    return amount
