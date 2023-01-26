from datetime import timedelta

from django.utils import timezone

from ledger.utils.cache import cache_for
from market.models import Trade


@cache_for()
def get_last_trades():
    trades = {}

    last_trades_qs = Trade.objects.filter(
        status=Trade.DONE
    ).exclude(trade_source=Trade.OTC).order_by('symbol', '-created')

    previous_trades_qs = last_trades_qs.filter(created__lte=timezone.now() - timedelta(hours=24))
    trades['today'] = {t.symbol_id: t.price for t in last_trades_qs.distinct('symbol')}
    trades['yesterday'] = {t.symbol_id: t.price for t in previous_trades_qs.distinct('symbol')}

    return trades
