import time

from django.conf import settings

if settings.TESTING:
    from accounts.models import Account, User, VerificationCode
    import random

    from collector.utils.price import price_redis
    from ledger.models import Asset, Trx, AddressBook, Network, NetworkAsset
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


    def set_up_user(self):
        phone = '09355913457'
        user = User.objects.create(username=phone, password='1', phone=phone)


    def generate_otp_code(user, scope) -> VerificationCode:
        otp_code = VerificationCode.objects.create(
            phone=user.phone,
            scope=scope,
            code='1',
            user=user, )
        return otp_code.code


    def new_network() -> Network:
        symbol = 'BSC'
        name = 'BSC'
        address_regex = '[1-9]'
        network = Network.objects.create(symbol=symbol, name=name, address_regex=address_regex)

        return network


    def new_network_asset(asset: Asset, network: Network):

        asset = asset
        network = network
        withdraw_fee = '0'
        withdraw_min = '1'
        withdraw_max = '1000'
        withdraw_precision = '1'
        network_asset = NetworkAsset.objects.create(
            asset=asset,
            network=network,
            withdraw_fee=withdraw_fee,
            withdraw_min=withdraw_min,
            withdraw_max=withdraw_max,
            withdraw_precision=withdraw_precision,
        )
        return network_asset


    def new_address_book(account, network, asset=None) -> AddressBook:
        name = 'test'
        address = 'addressbook1'
        account = account
        network = network
        if asset:
            asset = Asset.get(asset)
        address_book = AddressBook.objects.create(name=name, address=address, account=account, network=network,
                                                  asset=asset)
        return address_book
