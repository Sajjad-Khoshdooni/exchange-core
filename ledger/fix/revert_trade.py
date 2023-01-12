from accounts.models import User
from ledger.models import OTCTrade


def revert_otc_trades(user: User, min_otc_trade_id: int, max_otc_trade_id: int):
    trades = OTCTrade.objects.filter(
        otc_request__account__user=user,
        status=OTCTrade.DONE,
        id__range=(min_otc_trade_id, max_otc_trade_id),
    ).order_by('-id')

    for t in trades:
        print('reverting %s' % t)
        t.revert()
