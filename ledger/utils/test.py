import time

from django.conf import settings

if settings.TESTING:
    from accounts.models import Account, User
    import random

    from collector.utils.price import price_redis
    from ledger.models import Asset, Trx
    from uuid import uuid4


    def get_rand_int():
        return random.randint(0, 100000000)


    def new_account() -> Account:
        name = 'test' + str(get_rand_int())
        u = User.objects.create(username=name, phone=name)
        return u.account


    def new_trx(account: Account, asset: Asset, amount):
        return Trx.transaction(
            sender=asset.get_wallet(Account.out()),
            receiver=asset.get_wallet(account),
            amount=amount,
            scope=Trx.TRANSFER,
            group_id=str(uuid4())
        )


    def set_price(asset: Asset, ask: float, bid: float = None):
        if not bid:
            bid = ask

        assert ask >= bid

        mapping = {
            'a': ask,
            'b': bid
        }

        if asset.symbol == Asset.USDT:
            key = 'nob:usdtirt'
        else:
            key = 'bin:' + asset.symbol.lower() + 'usdt'

        price_redis.hset(name=key, mapping=mapping)

        time.sleep(1)
