import dataclasses
from datetime import timedelta

from django.db.models import Sum, Max
from django.utils import timezone

from accounts.models.login_activity import LoginActivity
from ledger.models import Transfer

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

    return not bool(risks)


@dataclasses.dataclass
class RiskFactor:
    MULTIPLE_DEVICES = 'multiple-devices'
    DAY_HIGH_WITHDRAW = 'day-high-withdraw-value'
    FIRST_WITHDRAW = 'first-withdraw'
    WITHDRAW_VALUE_PEAK = 'withdraw-value-peak'
    HIGH_DEPOSITS_VALUE = 'high-deposits-value'
    HIGH_TRANSFERS_COUNT = 'high-transfers-count'

    reason: str
    value: float
    expected: float


def get_withdraw_risks(transfer: Transfer) -> list:
    risks = []
    user = transfer.wallet.account.user

    transfers = Transfer.objects.filter(
        wallet__account=transfer.wallet.account
    )

    withdraws = transfers.filter(deposit=False)

    devices = LoginActivity.objects.filter(user=user).values('device').distinct().count()
    if devices > 1:
        risks.append(
            RiskFactor(
                reason=RiskFactor.MULTIPLE_DEVICES,
                value=devices,
                expected=1,
            )
        )

    current_day_withdraw_value = withdraws.filter(
        created__gte=timezone.now() - timedelta(days=1)
    ).aggregate(value=Sum('usdt_value'))['value'] or 0

    safe_daily_withdraw_value = SAFE_DAILY_WITHDRAW_VALUE * transfer.wallet.account.user.withdraw_risk_level_multiplier

    if current_day_withdraw_value > safe_daily_withdraw_value:
        risks.append(
            RiskFactor(
                reason=RiskFactor.DAY_HIGH_WITHDRAW,
                value=float(current_day_withdraw_value),
                expected=float(safe_daily_withdraw_value),
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
    else:
        max_withdraw_value = withdraws.filter(
            created__range=(timezone.now() - timedelta(days=31), timezone.now() - timedelta(days=1))
        ).aggregate(value=Max('usdt_value'))['value'] or 0

        if current_day_withdraw_value > max_withdraw_value * 2:
            risks.append(
                RiskFactor(
                    reason=RiskFactor.WITHDRAW_VALUE_PEAK,
                    value=float(current_day_withdraw_value),
                    expected=float(max_withdraw_value * 2)
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
