from uuid import uuid4

from accounts.models import User
from ledger.models import OTCTrade, Wallet, Trx
from ledger.utils.wallet_pipeline import WalletPipeline


def revert_otc_trades(user: User, min_otc_trade_id: int, max_otc_trade_id: int):
    trades = OTCTrade.objects.filter(
        otc_request__account__user=user,
        status=OTCTrade.DONE,
        id__range=(min_otc_trade_id, max_otc_trade_id),
    ).order_by('-id')

    for t in trades:
        print('reverting %s' % t)
        t.revert()

    clear_debt(user)


def clear_debt(user: User):
    spot_wallets_list = Wallet.objects.filter(account=user.account, market=Wallet.SPOT).exclude(balance=0)
    spot_dict = {w.asset: w for w in spot_wallets_list}
    debt_wallets_list = Wallet.objects.filter(account=user.account, market=Wallet.DEBT).exclude(balance=0)
    debt_dict = {w.asset: w for w in debt_wallets_list}

    to_clear_assets = set(spot_dict) & set(debt_dict)

    for asset in to_clear_assets:
        sw = spot_dict[asset]
        dw = debt_dict[asset]

        amount = min(sw.balance, -dw.balance)

        if amount > 0:
            with WalletPipeline() as pipeline:
                pipeline.new_trx(
                    sender=sw,
                    receiver=dw,
                    amount=amount,
                    scope='dc',
                    group_id=uuid4()
                )
