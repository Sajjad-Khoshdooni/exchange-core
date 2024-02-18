import dataclasses
from decimal import Decimal

from django.db.models import Sum

from financial.models import FiatWithdrawRequest, Payment
from ledger.utils.fields import CANCELED
from ledger.utils.withdraw_verify import RiskFactor, get_common_system_risks


def auto_verify_fiat_withdraw(withdraw: FiatWithdrawRequest):
    system_risks = get_fiat_withdraw_risks(withdraw)
    common_system_risks = get_common_system_risks(withdraw.bank_account.user.get_account())

    risks = [*common_system_risks, *system_risks]

    if risks:
        withdraw.risks = list(map(dataclasses.asdict, risks))
        withdraw.save(update_fields=['risks'])

    return not bool(risks)


def get_fiat_withdraw_risks(withdraw: FiatWithdrawRequest) -> list:
    user = withdraw.bank_account.user
    risks = []

    total_deposits = Payment.objects.filter(
        user=user
    ).exclude(status=CANCELED).aggregate(
        amount=Sum('amount')
    )['amount'] or 0

    total_withdraws = FiatWithdrawRequest.objects.filter(
        bank_account__user=user
    ).exclude(status=CANCELED).aggregate(amount=Sum('amount'))['amount'] or 0

    expected = Decimal('1.2') * total_deposits

    if total_withdraws > expected:
        risks.append(
            RiskFactor(
                reason=RiskFactor.HIGH_WITHDRAW,
                value=float(total_withdraws),
                expected=float(expected),
            )
        )

    gateway = withdraw.gateway
    if gateway.max_auto_withdraw_amount is not None and withdraw.amount > gateway.max_auto_withdraw_amount:
        risks.append(
            RiskFactor(
                reason=RiskFactor.AUTO_WITHDRAW_CEIL,
                value=withdraw.amount,
                expected=gateway.max_auto_withdraw_amount,
            )
        )

    total_withdraws = FiatWithdrawRequest.objects.exclude(status=CANCELED).aggregate(sum=Sum('amount'))['sum'] or 0
    account_trade_volume = withdraw.bank_account.user.account.trade_volume_irt

    if total_withdraws > account_trade_volume * 2 and total_withdraws > 2_000_000:
        risks.append(
            RiskFactor(
                reason=RiskFactor.SMALL_TRADE_RATIO,
                value=total_withdraws,
                expected=account_trade_volume * 2,
            )
        )

    return risks
