from decimal import Decimal

from accounts.models import User
from financial.models import Payment, FiatWithdrawRequest
from ledger.models import Wallet
from ledger.utils.fields import DONE
from ledger.utils.price import BUY, get_trading_price_irt


def get_user_irt_net_deposit(user: User) -> int:

    irt_deposits = Payment.objects.filter(
        payment_request__bank_card__user=user,
        status=DONE
    ).order_by('created').values_list('created', 'payment_request__amount')

    irt_withdraws = FiatWithdrawRequest.objects.filter(
        bank_account__user=user,
        status=DONE
    ).order_by('created').values_list('created', 'amount')

    net_irt_transfers = list(irt_deposits) + [(created, -amount) for (created, amount) in irt_withdraws]

    net_irt_transfers.sort(key=lambda x: x[0])

    irt_values = list(map(lambda x: x[1], net_irt_transfers))

    net_deposit = 0

    for value in irt_values:
        net_deposit += value

        if net_deposit < 0:
            net_deposit = 0

    return net_deposit
    
    
def check_withdraw_laundering(wallet: Wallet, amount: Decimal) -> bool:
    user = wallet.account.user

    if user >= User.LEVEL3:
        return True

    net_irt_deposit = get_user_irt_net_deposit(user)

    if net_irt_deposit <= 1000:
        return True

    total_irt_value = wallet.account.get_total_balance_irt(Wallet.SPOT, side=BUY)

    price = get_trading_price_irt(wallet.asset.symbol, side=BUY, raw_price=True)

    return amount * price <= total_irt_value - net_irt_deposit
