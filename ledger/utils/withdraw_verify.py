import dataclasses
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum, Max
from django.utils import timezone

from accounts.models import Account
from accounts.models.login_activity import LoginActivity
from ledger.models import Transfer, Wallet

WHITELIST_DAILY_WITHDRAW_VALUE = 50
SAFE_DAILY_WITHDRAW_VALUE = 150
SAFE_CURRENT_DEPOSITS_VALUE = 500
SAFE_CURRENT_TRANSFERS_COUNT = 6


def auto_withdraw_verify(transfer: Transfer) -> bool:
    assert not transfer.deposit

    if transfer.wallet.account.user.withdraw_limit_whitelist:
        return True

    risks = get_withdraw_risks(transfer)

    if risks:
        transfer.risks = list(map(dataclasses.asdict, risks))
        transfer.save(update_fields=['risks'])

        if risks[0].whitelist:
            return True

    return not bool(risks)


@dataclasses.dataclass
class RiskFactor:
    MULTIPLE_DEVICES = 'multiple-devices'
    DAY_HIGH_WITHDRAW = 'day-high-withdraw-value'
    FIRST_WITHDRAW = 'first-withdraw'
    WITHDRAW_VALUE_PEAK = 'withdraw-value-peak'
    HIGH_DEPOSITS_VALUE = 'high-deposits-value'
    HIGH_TRANSFERS_COUNT = 'high-transfers-count'
    MISMATCH_OUTPUT_INPUT = 'mismatch-output-input'
    HIGH_WITHDRAW = 'high-withdraw'
    AUTO_WITHDRAW_CEIL = 'auto-withdraw-ceil'
    INVALID_DESTINATION = 'invalid-destination'

    reason: str
    value: float
    expected: float
    whitelist: bool = False


def get_withdraw_risks(transfer: Transfer) -> list:
    risks = []
    user = transfer.wallet.account.user

    transfers = Transfer.objects.filter(
        wallet__account=transfer.wallet.account
    )

    withdraws = transfers.filter(deposit=False)

    current_day_withdraw_value = withdraws.filter(
        created__gte=timezone.now() - timedelta(days=1)
    ).aggregate(value=Sum('usdt_value'))['value'] or 0

    account_safety_multiplier = transfer.wallet.account.user.withdraw_risk_level_multiplier

    safe_daily_withdraw_value = SAFE_DAILY_WITHDRAW_VALUE * account_safety_multiplier
    whitelist_daily_withdraw_value = WHITELIST_DAILY_WITHDRAW_VALUE * account_safety_multiplier

    if current_day_withdraw_value > safe_daily_withdraw_value:
        risks.append(
            RiskFactor(
                reason=RiskFactor.DAY_HIGH_WITHDRAW,
                value=float(current_day_withdraw_value),
                expected=float(safe_daily_withdraw_value),
            )
        )
    elif current_day_withdraw_value <= whitelist_daily_withdraw_value:
        return [
            RiskFactor(
                reason=RiskFactor.DAY_HIGH_WITHDRAW,
                value=float(current_day_withdraw_value),
                expected=float(whitelist_daily_withdraw_value),
                whitelist=True
            )
        ]

    devices = LoginActivity.objects.filter(user=user).values('device').distinct().count()
    if devices > 1:
        risks.append(
            RiskFactor(
                reason=RiskFactor.MULTIPLE_DEVICES,
                value=devices,
                expected=1,
            )
        )

    if withdraws.count() == 1:
        risks.append(
            RiskFactor(
                reason=RiskFactor.FIRST_WITHDRAW,
                value=1,
                expected=0
            )
        )

    current_withdraws = withdraws.filter(
        created__range=(timezone.now() - timedelta(days=31), timezone.now() - timedelta(days=1))
    )

    if current_withdraws.count() > 2:
        max_withdraw_value = current_withdraws.aggregate(value=Max('usdt_value'))['value'] or 0
        expected_withdraw_value = max_withdraw_value * 2

        if transfer.usdt_value > max(expected_withdraw_value, 50):
            risks.append(
                RiskFactor(
                    reason=RiskFactor.WITHDRAW_VALUE_PEAK,
                    value=float(current_day_withdraw_value),
                    expected=float(expected_withdraw_value)
                )
            )

    deposits_value = transfers.filter(
        deposit=True,
        created__gte=timezone.now() - timedelta(days=3)
    ).aggregate(value=Sum('usdt_value'))['value'] or 0

    if deposits_value > SAFE_CURRENT_DEPOSITS_VALUE:
        risks.append(
            RiskFactor(
                reason=RiskFactor.HIGH_DEPOSITS_VALUE,
                value=float(deposits_value),
                expected=SAFE_CURRENT_DEPOSITS_VALUE
            )
        )

    transfer_counts = transfers.filter(
        created__gte=timezone.now() - timedelta(days=3)
    ).count()

    if transfer_counts > SAFE_CURRENT_TRANSFERS_COUNT:
        risks.append(
            RiskFactor(
                reason=RiskFactor.HIGH_TRANSFERS_COUNT,
                value=transfer_counts,
                expected=SAFE_CURRENT_TRANSFERS_COUNT
            )
        )

    return risks


def can_withdraw(account: Account):
    if not settings.WITHDRAW_ENABLE or not account.user.can_withdraw:
        return False

    if Wallet.objects.filter(account=account, market=Wallet.DEBT, balance__lt=0):
        return False

    return True
