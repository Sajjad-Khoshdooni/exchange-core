import uuid
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounting.models import TradeRevenue, Account
from accounts.models import User, LoginActivity, TrafficSource
from analytics.event.producer import get_kafka_producer
from analytics.models import ActiveTrader, EventTracker
from analytics.utils.dto import UserEvent, LoginEvent, TransferEvent, TrafficSourceEvent, StakeRequestEvent, PrizeEvent, \
    TradeEvent
from financial.models import FiatWithdrawRequest, Payment
from ledger.models import Transfer, Prize, OTCTrade, FastBuyToken
from ledger.utils.external_price import get_external_price
from ledger.utils.fields import DONE
from market.models import Trade
from stake.models import StakeRequest


@shared_task(queue='history')
def create_analytics(now=None):
    if not now:
        now = timezone.now()

    for period in ActiveTrader.PERIODS:
        start = now - timedelta(days=period)

        accounts = set(TradeRevenue.objects.filter(
            created__range=(start, now)
        ).values_list('account', flat=True).distinct())

        old_accounts = set(TradeRevenue.objects.filter(
            created__range=(start - timedelta(days=1), now - timedelta(days=1))
        ).values_list('account', flat=True).distinct())

        ActiveTrader.objects.get_or_create(
            created=now,
            period=period,
            defaults={
                'active': len(accounts),
                'churn': len(old_accounts - accounts),
                'new': len(accounts - old_accounts),
            }
        )


@shared_task(queue='history')
def trigger_kafka_event():
    producer = get_kafka_producer()
    tracker, _ = EventTracker.objects.get_or_create(name='kafka')

    # user = User.objects.filter(id=tracker.last_user_id + 1).first()
    # if user:
    #     if not hasattr(user, 'account'):
    #         account = user.get_account()
    #     else:
    #         account = user.account
    #     referrer_id = account and account.referred_by and account.referred_by.owner.user_id
    #     event = UserEvent(
    #         user_id=user.id,
    #         first_name=user.first_name,
    #         last_name=user.last_name,
    #         referrer_id=referrer_id,
    #         created=user.date_joined,
    #         event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(user.id) + UserEvent.type),
    #         level_2_verify_datetime=user.level_2_verify_datetime,
    #         level_3_verify_datetime=user.level_3_verify_datetime,
    #         level=user.level,
    #         birth_date=user.birth_date,
    #         can_withdraw=user.can_withdraw,
    #         can_trade=user.can_trade,
    #         promotion=user.promotion,
    #         chat_uuid=user.chat_uuid,
    #         verify_status=user.verify_status,
    #         reject_reason=user.reject_reason,
    #         first_fiat_deposit_date=user.first_fiat_deposit_date,
    #         first_crypto_deposit_date=user.first_crypto_deposit_date,
    #     )
    #     producer.produce(event)

    login_activity = LoginActivity.objects.filter(id=tracker.last_login_id + 1).first()
    if login_activity:
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

    transfer = Transfer.objects.filter(id=tracker.last_transfer_id + 1, status=Transfer.DONE).first()
    if transfer:
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

    fiat_transfer = FiatWithdrawRequest.objects.filter(
        id=tracker.last_fiat_withdraw_id + 1,
        status=FiatWithdrawRequest.DONE
    ).first()
    if fiat_transfer:
        event = TransferEvent(
            id=fiat_transfer.id,
            user_id=fiat_transfer.bank_account.user_id,
            amount=fiat_transfer.amount,
            coin='IRT',
            network='IRT',
            created=fiat_transfer.created,
            value_irt=fiat_transfer.amount,
            value_usdt=float(fiat_transfer.amount) / float(usdt_price),
            is_deposit=False,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(fiat_transfer.id) + TransferEvent.type)
        )

        producer.produce(event)

    payment = Payment.objects.filter(id=tracker.last_payment_id + 1, status=DONE).first()
    if payment:
        event = TransferEvent(
            id=payment.id,
            user_id=payment.payment_request.bank_card.user_id,
            amount=payment.payment_request.amount,
            coin='IRT',
            network='IRT',
            is_deposit=True,
            value_usdt=float(payment.payment_request.amount) / float(usdt_price),
            value_irt=payment.payment_request.amount,
            created=payment.created,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(payment.id) + TransferEvent.type)
        )

        producer.produce(event)

    trade = Trade.objects.filter(id=tracker.last_payment_id + 1, account__user__isnull=False).exclude(
            account__type=Account.SYSTEM
    ).first()
    if trade:
        event = TradeEvent(
            id=trade.id,
            user_id=trade.account.user_id,
            amount=trade.amount,
            price=trade.price,
            symbol=trade.symbol.name,
            trade_type='market',
            market=trade.market,
            created=trade.created,
            value_usdt=trade.usdt_value,
            value_irt=trade.irt_value,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(trade.id) + TradeEvent.type)
        )

        producer.produce(event)

    otc_trade = OTCTrade.objects.filter(
        id=tracker.last_otc_trade_id + 1,
        otc_request__account__user__isnull=False,
        status=OTCTrade.DONE).exclude(
            otc_request__account__type=Account.SYSTEM
    ).first()
    if otc_trade:
        trade_type = 'otc'

        req = otc_trade.otc_request
        if FastBuyToken.objects.filter(otc_request=req).exists():
            trade_type = 'fast_buy'

        event = TradeEvent(
            id=otc_trade.id,
            user_id=req.account.user_id,
            amount=req.amount,
            price=req.price,
            symbol=req.symbol.name,
            trade_type=trade_type,
            market=req.market,
            created=otc_trade.created,
            value_usdt=req.usdt_value,
            value_irt=req.irt_value,
            event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(otc_trade.id) + TradeEvent.type)
        )

        producer.produce(event)

    traffic_source = TrafficSource.objects.filter(id=tracker.last_traffic_source_id + 1, status=Transfer.DONE).first()
    if traffic_source:
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

    stake_request = StakeRequest.objects.filter(id=tracker.last_staking_id + 1, status=Transfer.DONE).first()
    if stake_request:
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

    prize = Prize.objects.filter(id=tracker.last_prize_id + 1, status=Transfer.DONE).first()
    if prize:
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
