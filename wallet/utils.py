from eth_account import Account

from wallet.models import Secret


def get_eth_address(secret: Secret):
    return Account.from_key(secret.key).address


def get_trx_address(secret: Secret):
    return '41' + Account.from_key(secret.key).address[2:]

