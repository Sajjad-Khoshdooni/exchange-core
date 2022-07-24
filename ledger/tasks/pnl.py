import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ledger.models import PNLHistory, Wallet, Asset
from ledger.utils.price import get_avg_tether_price_irt_grpc, get_tether_price_irt_grpc, BUY, get_tether_irt_price

logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def create_pnl_histories():
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_timestamp = int(today.timestamp() * 1000)

    if settings.DEBUG:
        usdt_price = get_tether_irt_price(BUY)
    else:
        usdt_price = get_avg_tether_price_irt_grpc(
            today_timestamp - 600_000, today_timestamp
        ) or get_tether_price_irt_grpc(BUY, today)

    all_in_out = PNLHistory.get_all_in_out(today - timedelta(days=1), today)
    all_wallets = PNLHistory.get_all_wallets()
    last_pnl_histories = PNLHistory.get_last_histories()
    pnl_accounts = set(map(lambda k: k[1], all_wallets))
    margin_accounts = set(map(lambda k: k[1], filter(lambda w: w[0] == Wallet.MARGIN, all_wallets)))

    to_create_pnl_histories = []
    for account in pnl_accounts:
        for market in (Wallet.SPOT, Wallet.MARGIN):
            if market == Wallet.MARGIN and account not in margin_accounts:
                continue
            last_usdt_snapshot = last_pnl_histories.get((account, market, Asset.USDT), 0)
            snapshot_balance, profit = PNLHistory.calculate_amounts_in_usdt(
                PNLHistory.get_for_account_market(account, market, all_wallets.items()),
                PNLHistory.get_for_account_market(account, market, all_in_out.items()),
                last_usdt_snapshot,
                usdt_price
            )
            to_create_pnl_histories.append(
                PNLHistory(
                    date=today,
                    account_id=account,
                    market=market,
                    base_asset=Asset.USDT,
                    snapshot_balance=snapshot_balance,
                    profit=profit if last_usdt_snapshot else 0,
                )
            )
            if market == Wallet.SPOT:
                irt_snapshot = snapshot_balance * usdt_price
                last_irt_snapshot = last_pnl_histories.get((account, market, Asset.IRT), 0)
                if last_irt_snapshot:
                    last_usdt_price = last_usdt_snapshot / last_irt_snapshot
                    irt_profit = (profit * usdt_price) + (usdt_price - last_usdt_price) * last_usdt_snapshot
                else:
                    irt_profit = 0

                to_create_pnl_histories.append(
                    PNLHistory(
                        date=today,
                        account_id=account,
                        market=market,
                        base_asset=Asset.IRT,
                        snapshot_balance=irt_snapshot,
                        profit=irt_profit,
                    )
                )

    PNLHistory.objects.bulk_create(to_create_pnl_histories)
