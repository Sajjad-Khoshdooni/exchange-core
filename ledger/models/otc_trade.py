from uuid import uuid4

from django.db import models, transaction

from accounts.models import Account
from ledger.models import OTCRequest, Trx, BalanceLock
from provider.models import ProviderOrder


class TokenExpired(Exception):
    pass


class OTCTrade(models.Model):
    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

    created = models.DateTimeField(auto_now_add=True)
    otc_request = models.OneToOneField('ledger.OTCRequest', on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4, db_index=True)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)]
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE)

    def change_status(self, status: str):
        self.status = status
        self.save()

    def create_ledger(self):
        system = Account.system()
        user = self.otc_request.account

        from_asset = self.otc_request.from_asset
        to_asset = self.otc_request.to_asset

        with transaction.atomic():
            Trx.objects.bulk_create([
                Trx(
                    sender=from_asset.get_wallet(user),
                    receiver=from_asset.get_wallet(system),
                    amount=self.otc_request.from_amount,
                    group_id=self.group_id
                ),
                Trx(
                    sender=to_asset.get_wallet(system),
                    receiver=to_asset.get_wallet(user),
                    amount=self.otc_request.to_amount,
                    group_id=self.group_id
                ),
            ])
    
    @property
    def client_order_id(self):
        return 'otc-%s' % self.id

    @classmethod
    def execute_trade(cls, otc_request: OTCRequest) -> 'OTCTrade':

        if otc_request.expired():
            raise TokenExpired()

        account = otc_request.account

        from_asset = otc_request.from_asset

        conf = otc_request.get_trade_config()

        assert conf.coin.is_trade_amount_valid(conf.coin_amount)

        from_wallet = from_asset.get_wallet(account)
        from_wallet.can_buy(otc_request.from_amount, raise_exception=True)  # use select for update for more guarantee!

        with transaction.atomic():
            lock = BalanceLock.objects.create(
                wallet=from_wallet,
                amount=otc_request.from_amount
            )

            otc_trade = OTCTrade.objects.create(
                otc_request=otc_request,
                lock=lock
            )

        hedged = ProviderOrder.try_hedge_for_new_order(
            asset=conf.coin,
            side=conf.side,
            amount=conf.coin_amount
        )

        if hedged:
            with transaction.atomic():
                otc_trade.change_status(cls.DONE)
                otc_trade.create_ledger()
                otc_trade.lock.release()

        return otc_trade
