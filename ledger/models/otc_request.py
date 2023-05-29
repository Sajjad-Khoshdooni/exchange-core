import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.event.producer import get_kafka_producer
from accounts.models import Account
from accounts.utils.dto import TradeEvent
from ledger.exceptions import SmallAmountTrade
from ledger.models import Asset, Wallet
from ledger.utils.external_price import get_external_price, get_other_side, BUY
from ledger.utils.fields import get_amount_field
from ledger.utils.otc import get_trading_pair, get_otc_spread, spread_to_multiplier
from ledger.utils.precision import ceil_precision, floor_precision
from ledger.utils.random import secure_uuid4
from market.consts import OTC_MIN_HARD_FIAT_VALUE
from market.models import BaseTrade
from market.utils.trade import get_fee_info


class OTCRequest(BaseTrade):
    # EXPIRE_TIME = 6
    EXPIRATION_TIME = 11

    created = models.DateTimeField(auto_now_add=True)
    token = models.UUIDField(default=secure_uuid4, db_index=True)

    from_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='from_otc_requests')
    to_asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE, related_name='to_otc_requests')
    from_amount = get_amount_field(null=True)
    to_amount = get_amount_field(null=True)

    @property
    def is_maker(self) -> bool:
        return False

    @classmethod
    def new_trade(cls, account: Account, market: str, from_asset: Asset, to_asset: Asset, from_amount: Decimal = None,
                  to_amount: Decimal = None, allow_dust: bool = False, check_enough_balance: bool = True) -> 'OTCRequest':

        assert from_amount or to_amount
        assert (from_amount or to_amount) > 0

        otc_request = cls.get_otc_request(
            account=account,
            from_asset=from_asset,
            to_asset=to_asset,
            from_amount=from_amount,
            to_amount=to_amount,
            market=market,
        )

        if not allow_dust:
            if otc_request.price * otc_request.amount * otc_request.base_irt_price < OTC_MIN_HARD_FIAT_VALUE:
                raise SmallAmountTrade()

        if check_enough_balance:
            from_wallet = from_asset.get_wallet(account, otc_request.market)
            from_wallet.has_balance(otc_request.get_paying_amount(), raise_exception=True, check_system_wallets=True)

        if otc_request.symbol.asset.otc_status not in (Asset.ACTIVE, otc_request.side):
            side_verbose = 'خرید' if otc_request.side == BUY else 'فروش'
            raise ValidationError('امکان %s این رمزارز وجود ندارد.' % side_verbose)

        otc_request.save()

        return otc_request

    @classmethod
    def get_otc_request(cls, account: Account, from_asset: Asset, to_asset: Asset, from_amount: Decimal = None,
                        to_amount: Decimal = None, market: str = Wallet.SPOT) -> 'OTCRequest':

        assert (from_amount or to_amount) and (not from_amount or not to_amount), 'exactly one amount should present'

        pair = get_trading_pair(from_asset, to_asset, from_amount, to_amount)
        assert pair.base.symbol in (Asset.IRT, Asset.USDT)
        from market.models import PairSymbol

        symbol = PairSymbol.objects.get(asset=pair.coin, base_asset=pair.base)

        otc_request = OTCRequest(
            account=account,
            from_asset=from_asset,
            to_asset=to_asset,
            market=market,
            from_amount=from_amount,
            to_amount=to_amount,

            symbol=symbol,
            side=pair.side,
        )

        other_side = get_other_side(pair.side)
        usdt_irt_price = get_external_price(
            coin=Asset.USDT,
            base_coin=Asset.IRT,
            side=other_side,
            allow_stale=True,
        )

        if pair.base.symbol == Asset.USDT:
            otc_request.base_usdt_price = 1
            otc_request.base_irt_price = usdt_irt_price
        else:
            otc_request.base_usdt_price = 1 / usdt_irt_price
            otc_request.base_irt_price = 1

        if pair.base_amount is not None:
            trade_value = pair.base_amount * otc_request.base_usdt_price
        else:
            coin_usdt_price = get_external_price(
                coin=pair.coin.symbol,
                base_coin=Asset.USDT,
                side=other_side,
            )

            trade_value = pair.coin_amount * coin_usdt_price

        spread = get_otc_spread(
            coin=pair.coin.symbol,
            base_coin=pair.base.symbol,
            value=trade_value,
            side=other_side
        )

        coin_price = get_external_price(
            coin=pair.coin.symbol,
            base_coin=pair.base.symbol,
            side=other_side,
        )
        otc_request.price = ceil_precision(coin_price * spread_to_multiplier(spread, other_side), symbol.tick_size)

        if pair.coin_amount is not None:
            amount = pair.coin_amount
        else:
            amount = pair.base_amount / otc_request.price

        otc_request.amount = floor_precision(amount, symbol.step_size)

        fee_info = get_fee_info(otc_request)

        otc_request.fee_amount = fee_info.trader_fee_amount
        otc_request.fee_usdt_value = fee_info.trader_fee_value
        otc_request.fee_revenue = fee_info.fee_revenue

        return otc_request

    def get_expire_time(self) -> datetime:
        return self.created + timedelta(seconds=OTCRequest.EXPIRATION_TIME)

    def expired(self):
        return (timezone.now() - self.created).total_seconds() >= self.EXPIRATION_TIME

    def __str__(self):
        return '%s %s in %s' % (self.side, self.amount, self.symbol)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(
                from_amount__gte=0,
                to_amount__gte=0,
            ), name='check_ledger_otc_request_amounts', ),

            CheckConstraint(check=Q(
                amount__gte=0,
                price__gte=0,
                fee_amount__gte=0,
            ), name='otc_request_check_trade_amounts', ),
        ]


@receiver(post_save, sender=OTCRequest)
def handle_OTC_trade_save(sender, instance, created, **kwargs):
    from ledger.models import FastBuyToken

    producer = get_kafka_producer()
    trade_type = 'otc'
    if FastBuyToken.objects.filter(otc_request=instance).exists():
        trade_type = 'fast_buy'

    event = TradeEvent(
        id=instance.id,
        user_id=instance.account.user.id,
        amount=instance.amount,
        price=instance.price,
        symbol=instance.symbol.name,
        trade_type=trade_type,
        market=instance.market,
        created=instance.created,
        value_usdt=float(instance.base_irt_price) * float(instance.amount),
        value_irt=float(instance.base_usdt_price) * float(instance.amount),
        event_id=str(uuid.uuid4())
    )

    producer.produce(event)
