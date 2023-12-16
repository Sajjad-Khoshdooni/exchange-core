from decimal import Decimal

from django.db.models import F, Sum
from rest_framework.exceptions import ValidationError

from accounts.models import Account, SmsNotification, Notification
from ledger.models import Wallet
from ledger.utils.external_price import LONG, BUY, SELL, SHORT, USDT, IRT
from market.models import PairSymbol


def check_margin_view_permission(account: Account, symbol: PairSymbol = None):
    user = account.user

    assert user

    if symbol and (not user.show_margin or not symbol.margin_enable):
        raise ValidationError('شما نمی‌توانید این عملیات را انجام دهید.')

    if not user.margin_quiz_pass_date:
        raise ValidationError('لطفا ابتدا به سوالات آزمون معاملات تعهدی پاسخ دهید.')


def alert_liquidate(position):
    try:
        Notification.objects.get_or_create(
            recipient=position.account.user,
            group_id=position.group_id,
            defaults={
                'title': 'لیکویید شدن موقعیت',
                'message': f'کاربر گرامی موقعیت {position.symbol.name} شما لیکویید شد.',
                'hidden': False,
                'push_status': Notification.PUSH_WAITING,
                'source': 'core'
            }
        )
    except:
        pass


def alert_position_warning(positions):
    for position in positions:
        if not position.alert_mode:
            SmsNotification.objects.get_or_create(
                recipient=position.account.user,
                group_id=position.group_id,
                defaults={
                    'content': f'کاربر گرامی موقعیت {position.symbol.name} شما نزدیک به لیکویید شدن است.',
                }
            )
    positions.update(alert_mode=True)


def check_margin_order(account, attrs):
    assert attrs['wallet']['market'] == Wallet.MARGIN

    from ledger.models import MarginLeverage, MarginPosition
    from accounts.models import SystemConfig

    if attrs.get('is_open_position') is None:
        raise ValidationError('Cant place margin order without is_open_position')

    if attrs.get('is_open_position') and attrs['side'] == BUY:
        margin_leverage, _ = MarginLeverage.objects.get_or_create(account=account)

        if margin_leverage.leverage == Decimal('1'):
            raise ValidationError('Cant place Long Buy margin order with Leverage 1')

    if attrs.get('is_open_position'):
        position_side = SHORT if attrs['side'] == SELL else LONG
    else:
        position_side = SHORT if attrs['side'] == BUY else LONG

    if MarginPosition.objects.filter(
            account=account,
            symbol__name=attrs['symbol']['name'].upper(),
            status=MarginPosition.TERMINATING,
            side=position_side
    ).exists():
        raise ValidationError('Cant place margin order Due to Terminating position')

    if attrs.get('is_open_position'):
        base = USDT if attrs['symbol']['name'].upper().endswith(USDT) else IRT
        sys_config = SystemConfig.get_system_config()
        total_equity = MarginPosition.objects.filter(
            status__in=[MarginPosition.TERMINATING, MarginPosition.OPEN],
            symbol__base_asset__symbol=base
        ).annotate(base_asset_value=F('asset_wallet__balance') * F('symbol__last_trade_price')).\
            aggregate(total_equity=Sum('base_asset_value') + Sum('base_wallet__balance'))['total_equity'] or 0

        if (base == USDT and total_equity >= sys_config.total_margin_usdt_base) or \
                (base == IRT and total_equity >= sys_config.total_margin_irt_base):
            raise ValidationError('Cant place margin order Due to reach total Equity limit')

        user_total_equity = MarginPosition.objects.filter(
            account=account,
            status__in=[MarginPosition.TERMINATING, MarginPosition.OPEN],
            symbol__base_asset__symbol=base
        ).annotate(base_asset_value=F('asset_wallet__balance') * F('symbol__last_trade_price')).\
            aggregate(total_equity=Sum('base_asset_value') + Sum('base_wallet__balance'))['total_equity'] or 0

        if (base == USDT and user_total_equity >= sys_config.total_user_margin_usdt_base) or \
                (base == IRT and user_total_equity >= sys_config.total_user_margin_irt_base):
            raise ValidationError('Cant place margin order Due to reach total Equity limit')
