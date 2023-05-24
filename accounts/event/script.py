import uuid

from financial.models import FiatWithdrawRequest, Payment
from ledger.models import OTCTrade
from ledger.models.transfer import Transfer
from ledger.utils.external_price import get_external_price
from market.models import Trade
from .producer import get_kafka_producer
from ..models import User, Account
from ..models.login_activity import LoginActivity
from ..utils.dto import UserEvent, LoginEvent, TransferEvent, TradeEvent


def produce_event(time_range):
    producer = get_kafka_producer()

    for user in User.objects.filter(date_joined__range=time_range):
        referrer_id = None
        account = Account.objects.filter(user=user)[0]
        referrer = account and account.referred_by and account.referred_by.owner.user

        if referrer:
            referrer_id = account.referred_by.owner.user.id

        event = UserEvent(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            referrer_id=referrer_id,
            created=user.created,
            event_id=uuid.uuid4()
        )
        producer.produce(event)

    for login_activity in LoginActivity.objects.filter(created__range=time_range):
        event = LoginEvent(
            user_id=login_activity.user.id,
            device=login_activity.device,
            is_signup=login_activity.is_sign_up,
            created=login_activity.created,
            event_id=uuid.uuid4()
        )

        producer.produce(event)

    for transfer in Transfer.objects.filter(created__range=time_range, status=Transfer.DONE):
        event = TransferEvent(
            id=transfer.id,
            user_id=transfer.wallet.account.user.id,
            amount=transfer.amount,
            coin=transfer.wallet.asset.symbol,
            network=transfer.network.symbol,
            created=transfer.created,
            is_deposit=transfer.deposit,
            value_irt=transfer.irt_value,
            value_usdt=transfer.usdt_value,
            event_id=transfer.group_id
        )

        producer.produce(event)

    usdt_price = get_external_price(coin='USDT', base_coin='IRT', side='buy')
    for transfer in FiatWithdrawRequest.objects.filter(created__range=time_range, status=FiatWithdrawRequest.DONE):
        event = TransferEvent(
            id=transfer.id,
            user_id=transfer.bank_account.user.id,
            amount=transfer.amount,
            coin='IRT',
            network='IRT',
            created=transfer.created,
            value_irt=transfer.amount,
            value_usdt=float(transfer.amount) / float(usdt_price),
            is_deposit=False,
            event_id=transfer.group_id
        )

        producer.produce(event)

    for transfer in Payment.objects.filter(created__range=time_range, status='done'):
        event = TransferEvent(
            id=transfer.id,
            user_id=transfer.payment_request.bank_card.user.id,
            amount=transfer.payment_request.amount,
            coin='IRT',
            network='IRT',
            is_deposit=True,
            value_usdt=float(transfer.payment_request.amount) / float(usdt_price),
            value_irt=transfer.payment_request.amount,
            created=transfer.created,
            event_id=transfer.group_id
        )

        producer.produce(event)

    for trade in Trade.objects.filter(created__range=time_range):
        event = TradeEvent(
            id=trade.id,
            user_id=trade.account.user.id,
            amount=trade.amount,
            price=trade.price,
            symbol=trade.symbol,
            trade_type='market',
            market=trade.market,
            created=trade.created,
            value_usdt=float(trade.base_irt_price) * float(trade.amount),
            value_irt=float(trade.base_usdt_price) * float(trade.amount),
            event_id=uuid.uuid4()
        )

        producer.produce(event)

    for trade in OTCTrade.objects.filter(created__range=time_range):
        event = TradeEvent(
            id=trade.id,
            user_id=trade.account.user.id,
            amount=trade.amount,
            price=trade.price,
            symbol=trade.symbol,
            trade_type='otc',
            market=trade.market,
            created=trade.created,
            value_usdt=float(trade.base_irt_price) * float(trade.amount),
            value_irt=float(trade.base_usdt_price) * float(trade.amount),
            event_id=uuid.uuid4()
        )

        producer.produce(event)
