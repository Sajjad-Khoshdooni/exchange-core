import uuid
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounting.models import TradeRevenue
from accounts.models import User, LoginActivity, TrafficSource, Account
from analytics.event.producer import get_kafka_producer
from analytics.models import ActiveTrader, EventTracker
from analytics.utils.dto import LoginEvent, TransferEvent, TrafficSourceEvent, StakeRequestEvent, PrizeEvent, \
    TradeEvent, UserEvent
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
    print('history')
    # tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.USER)
    # user_list = list(User.objects.filter(
    #     id__gt=tracker.last_id
    # ).values_list('id', flat=True))
    # trigger_users_event.delay(user_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.TRANSFER)
    transfer_list = list(Transfer.objects.filter(
        id__gt=tracker.last_id, status=Transfer.DONE
    ).values_list('id', flat=True))
    trigger_transfer_event.delay(transfer_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.FIAT_WITHDRAW)
    fiat_transfer_list = list(FiatWithdrawRequest.objects.filter(
        id__gt=tracker.last_id,
        status=FiatWithdrawRequest.DONE
    ).values_list('id', flat=True))
    trigger_fiat_transfer_event.delay(fiat_transfer_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.PAYMENT)
    payment_list = list(Payment.objects.filter(
        id__gt=tracker.last_id, status=DONE
    ).values_list('id', flat=True))
    trigger_payment_event.delay(payment_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.TRADE)
    trade_list = list(Trade.objects.filter(
        id__gt=tracker.last_id, account__user__isnull=False
    ).exclude(
        account__type=Account.SYSTEM
    ).values_list('id', flat=True))
    trigger_trade_event.delay(trade_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.OTC_TRADE)
    otc_trade_list = list(OTCTrade.objects.filter(
        id__gt=tracker.last_id,
        otc_request__account__user__isnull=False,
        status=OTCTrade.DONE
    ).exclude(
        otc_request__account__type=Account.SYSTEM
    ).values_list('id', flat=True))
    trigger_otc_trade.delay(otc_trade_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.LOGIN)
    login_activity_list = list(LoginActivity.objects.filter(
        id__gt=tracker.last_id,
    ).values_list('id', flat=True))
    trigger_login_event.delay(login_activity_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.PRIZE)
    prize_list = list(Prize.objects.filter(
        id__gt=tracker.last_id,
    ).values_list('id', flat=True))
    trigger_prize_event.delay(prize_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.STAKING)
    stake_request_list = list(StakeRequest.objects.filter(
        id__gt=tracker.last_id, status=Transfer.DONE
    ).values_list('id', flat=True))
    trigger_stake_event.delay(stake_request_list)

    tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.TRAFFIC_SOURCE)
    traffic_source_list = list(TrafficSource.objects.filter(
        id__gt=tracker.last_id
    ).values_list('id', flat=True))
    trigger_traffic_source.delay(traffic_source_list)


@shared_task(queue='history')
def trigger_users_event(id_list):
    for user in User.objects.filter(id__in=id_list):
        if not hasattr(user, 'account'):
            account = user.get_account()
        else:
            account = user.account
        referrer_id = account and account.referred_by and account.referred_by.owner.user_id
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
        get_kafka_producer().produce(event)


@shared_task(queue='history')
def trigger_transfer_event(id_list):
    for transfer in Transfer.objects.filter(id__in=id_list):
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

        get_kafka_producer().produce(event, instance=transfer)


@shared_task(queue='history')
def trigger_fiat_transfer_event(id_list):
    usdt_price = get_external_price(coin='USDT', base_coin='IRT', side='buy')

    for fiat_transfer in FiatWithdrawRequest.objects.filter(id__in=id_list):
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

        get_kafka_producer().produce(event, instance=fiat_transfer)


@shared_task(queue='history')
def trigger_payment_event(id_list):
    usdt_price = get_external_price(coin='USDT', base_coin='IRT', side='buy')
    for payment in Payment.objects.filter(id__in=id_list):
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

        get_kafka_producer().produce(event, instance=payment)


@shared_task(queue='history')
def trigger_trade_event(id_list):
    for trade in Trade.objects.filter(id__in=id_list):
        if trade.account is None or \
                trade.account.user is None or \
                trade.account.type == Account.SYSTEM or \
                trade.account.user.id in [93167, 382]:
            continue

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

        get_kafka_producer().produce(event, instance=trade)


@shared_task(queue='history')
def trigger_otc_trade(id_list):
    for otc_trade in OTCTrade.objects.filter(id__in=id_list):
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

        get_kafka_producer().produce(event, instance=otc_trade)


@shared_task(queue='history')
def trigger_login_event(id_list):
    for login_activity in LoginActivity.objects.filter(id__in=id_list):
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

        get_kafka_producer().produce(event, instance=login_activity)


@shared_task(queue='history')
def trigger_prize_event(id_list):
    for prize in Prize.objects.filter(id__in=id_list):
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
        get_kafka_producer().produce(event, instance=prize)


@shared_task(queue='history')
def trigger_stake_event(id_list):
    for stake_request in StakeRequest.objects.filter(id__in=id_list):
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
        get_kafka_producer().produce(event, instance=stake_request)


@shared_task(queue='history')
def trigger_traffic_source(id_list):
    for traffic_source in TrafficSource.objects.filter(id__in=id_list):
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
        get_kafka_producer().produce(event, instance=traffic_source)
