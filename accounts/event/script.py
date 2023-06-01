import logging
import uuid
from datetime import timedelta, datetime

from django.utils import timezone

from accounts.event.producer import get_kafka_producer
from accounts.models import User, TrafficSource, Account
from accounts.models.login_activity import LoginActivity
from accounts.utils.dto import UserEvent, LoginEvent, TransferEvent, TradeEvent, TrafficSourceEvent, StakeRequestEvent, \
    PrizeEvent
from financial.models import FiatWithdrawRequest, Payment
from ledger.models import OTCTrade, FastBuyToken, Prize
from ledger.models.transfer import Transfer
from ledger.utils.external_price import get_external_price
from ledger.utils.fields import DONE
from market.models import Trade
from stake.models import StakeRequest

logger = logging.getLogger(__name__)


def reproduce_all(start: datetime = None, step: int = 30):
    if not start:
        start = User.objects.order_by('id').first().date_joined

    while start < timezone.now():
        end = start + timedelta(days=step)

        logger.info('Producing events of %s and %s' % (start, end))

        reproduce_events(start, end)

        start = end


def reproduce_events(start, end):
    producer = get_kafka_producer()

    time_range = (start, end)

    for user in User.objects.filter(date_joined__range=time_range):
        referrer_id = None
        account = user.get_account()
        referrer = account and account.referred_by and account.referred_by.owner.user

        if referrer:
            referrer_id = account.referred_by.owner.user_id

        event = UserEvent(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            referrer_id=referrer_id,
            created=user.date_joined,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(user.id) + UserEvent.type),
            level_2_verify_datetime=user.level_2_verify_datetime,
            level_3_verify_datetime=user.level_3_verify_datetime,
            level=user.level,
            birth_date=user.birth_date,
            can_withdraw=user.can_withdraw,
            can_trade=user.can_trade,
            promotion=user.promotion,
            chat_uuid=user.chat_uuid,
            verify_status=user.verify_status,
            reject_reason=user.reject_reason,
            first_fiat_deposit_date=user.first_fiat_deposit_date,
            first_crypto_deposit_date=user.first_crypto_deposit_date,
        )
        producer.produce(event)

    for login_activity in LoginActivity.objects.filter(created__range=time_range):
        event = LoginEvent(
            user_id=login_activity.user_id,
            device=login_activity.device,
            is_signup=login_activity.is_sign_up,
            created=login_activity.created,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(login_activity.id) + LoginEvent.type),
            user_agent=login_activity.user_agent,
            device_type=login_activity.device_type,
            location=login_activity.location,
            os=login_activity.os,
            browser=login_activity.browser,
            city=login_activity.city,
            country=login_activity.country,
            native_app=login_activity.native_app
        )

        producer.produce(event)

    for transfer in Transfer.objects.filter(created__range=time_range, status=Transfer.DONE).select_related('wallet__account', 'wallet__asset', 'network'):
        event = TransferEvent(
            id=transfer.id,
            user_id=transfer.wallet.account.user_id,
            amount=transfer.amount,
            coin=transfer.wallet.asset.symbol,
            network=transfer.network.symbol,
            created=transfer.created,
            is_deposit=transfer.deposit,
            value_irt=transfer.irt_value,
            value_usdt=transfer.usdt_value,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(transfer.id) + TransferEvent.type)
        )

        producer.produce(event)

    usdt_price = get_external_price(coin='USDT', base_coin='IRT', side='buy')

    for transfer in FiatWithdrawRequest.objects.filter(created__range=time_range, status=FiatWithdrawRequest.DONE).select_related('bank_account'):
        event = TransferEvent(
            id=transfer.id,
            user_id=transfer.bank_account.user_id,
            amount=transfer.amount,
            coin='IRT',
            network='IRT',
            created=transfer.created,
            value_irt=transfer.amount,
            value_usdt=float(transfer.amount) / float(usdt_price),
            is_deposit=False,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(transfer.id) + TransferEvent.type)
        )

        producer.produce(event)

    for transfer in Payment.objects.filter(created__range=time_range, status=DONE).select_related('payment_request__bank_card'):
        event = TransferEvent(
            id=transfer.id,
            user_id=transfer.payment_request.bank_card.user_id,
            amount=transfer.payment_request.amount,
            coin='IRT',
            network='IRT',
            is_deposit=True,
            value_usdt=float(transfer.payment_request.amount) / float(usdt_price),
            value_irt=transfer.payment_request.amount,
            created=transfer.created,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(transfer.id) + TransferEvent.type)
        )

        producer.produce(event)

    for trade in Trade.objects.filter(created__range=time_range, account__user__isnull=False).exclude(
            account__type=Account.SYSTEM
    ).select_related('account__user', 'symbol'):
        event = TradeEvent(
            id=trade.id,
            user_id=trade.account.user_id,
            amount=trade.amount,
            price=trade.price,
            symbol=trade.symbol.name,
            trade_type='market',
            market=trade.market,
            created=trade.created,
            value_usdt=float(trade.base_irt_price) * float(trade.amount),
            value_irt=float(trade.base_usdt_price) * float(trade.amount),
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(trade.id) + TradeEvent.type)
        )

        producer.produce(event)

    for trade in OTCTrade.objects.filter(created__range=time_range, otc_request__account__user__isnull=False, status=OTCTrade.DONE).exclude(
            otc_request__account__type=Account.SYSTEM
    ).select_related('otc_request__account__user', 'otc_request__symbol'):
        trade_type = 'otc'

        req = trade.otc_request
        if FastBuyToken.objects.filter(otc_request=req).exists():
            trade_type = 'fast_buy'

        event = TradeEvent(
            id=trade.id,
            user_id=req.account.user_id,
            amount=req.amount,
            price=req.price,
            symbol=req.symbol.name,
            trade_type=trade_type,
            market=req.market,
            created=req.created,
            value_usdt=float(req.irt_value),
            value_irt=float(req.usdt_value),
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(trade.id) + TradeEvent.type)
        )

        producer.produce(event)

    for traffic_source in TrafficSource.objects.filter(created__range=time_range):
        event = TrafficSourceEvent(
            created=traffic_source.created,
            user_id=traffic_source.user_id,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(traffic_source.id) + TrafficSourceEvent.type),
            utm_source=traffic_source.utm_source,
            utm_medium=traffic_source.utm_medium,
            utm_campaign=traffic_source.utm_campaign,
            utm_content=traffic_source.utm_content,
            utm_term=traffic_source.utm_term,
        )
        producer.produce(event)

    for stake_request in StakeRequest.objects.filter(created__range=time_range).select_related('account', 'stake_option'):
        event = StakeRequestEvent(
            created=stake_request.created,
            user_id=stake_request.account.user_id,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(stake_request.id) + StakeRequestEvent.type),
            stake_request_id=stake_request.id,
            stake_option_id=stake_request.stake_option.id,
            amount=stake_request.amount,
            status=stake_request.status,
            coin=stake_request.stake_option.asset.symbol,
            apr=stake_request.stake_option.apr
        )
        producer.produce(event)

    for prize in Prize.objects.filter(created__range=time_range):
        event = PrizeEvent(
            created=prize.created,
            user_id=prize.account.user_id,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(prize.id) + PrizeEvent.type),
            id=prize.id,
            amount=prize.amount,
            coin=prize.asset.symbol,
            voucher_expiration=prize.voucher_expiration,
            achievement_type=prize.achievement.type,
            value=prize.value
        )
        producer.produce(event)
