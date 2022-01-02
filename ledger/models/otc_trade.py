from decimal import Decimal
from uuid import uuid4

from django.db import models

from ledger.models import OTCRequest, Order, Asset
from ledger.utils.fields import get_amount_field
from provider.exchanges import BinanceHandler


class OTCTrade(models.Model):
    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

    created = models.DateTimeField(auto_now_add=True)
    otc_request = models.OneToOneField('ledger.OTCRequest', on_delete=models.PROTECT)

    amount = get_amount_field()
    group_id = models.UUIDField(default=uuid4, db_index=True)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)]
    )

    provider_order_id = models.CharField(
        max_length=16,
        blank=True
    )

    def change_status(self, status: str):
        self.status = status
        self.save()

    def create_ledger(self):
        pass
    
    @property
    def client_order_id(self):
        return 'otc-%s' % self.id

    @classmethod
    def create_trade(cls, otc_request: OTCRequest, amount: Decimal) -> 'OTCTrade':
        coin = otc_request.coin
        side = otc_request.side
        account = otc_request.account

        assert coin.is_trade_amount_valid(amount)

        if side == Order.BUY:
            market_wallet = Asset.get(Asset.IRT).get_wallet(account)
            market_amount = amount * otc_request.price
            market_wallet.can_buy(market_amount, raise_exception=True)
        else:
            wallet = coin.get_wallet(account)
            wallet.can_buy(amount, raise_exception=True)

        otc_trade = OTCTrade.objects.create(
            otc_request=otc_request,
            amount=amount,
        )

        resp = BinanceHandler.spot_place_order(
            symbol=coin.symbol + 'USDT',
            side=side,
            amount=amount,
            client_order_id=otc_trade.client_order_id
        )

        if resp:
            otc_trade.change_status(cls.DONE)
            otc_trade.create_ledger()
        else:
            otc_trade.change_status(cls.CANCELED)
        
        return otc_trade
