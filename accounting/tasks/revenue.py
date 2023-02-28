import logging
from collections import defaultdict

from celery import shared_task
from django.db.models import Sum, F

from accounting.models import TradeRevenue
from ledger.models import Asset
from ledger.utils.external_price import SELL
from ledger.utils.provider import get_provider_requester
from market.models import Trade, PairSymbol

logger = logging.getLogger(__name__)


@shared_task()
def fill_revenue_filled_prices():
    trade_revenues = TradeRevenue.objects.filter(
        coin_filled_price__isnull=True
    ).exclude(source=TradeRevenue.MANUAL).order_by('id').prefetch_related('symbol__asset', 'symbol__base_asset')

    delegated_hedges = defaultdict(list)
    usdt_irt_symbol = PairSymbol.objects.get(asset__symbol=Asset.USDT, base_asset__symbol=Asset.IRT)

    for revenue in trade_revenues:
        if revenue.source == TradeRevenue.USER:
            revenue.coin_filled_price = revenue.coin_price
            revenue.filled_amount = revenue.amount
            revenue.save(update_fields=['filled_amount', 'coin_filled_price'])

        elif revenue.source == TradeRevenue.OTC_MARKET:
            info = Trade.objects.filter(order_id=int(revenue.hedge_key)).aggregate(
                quote_cum=Sum(F('amount') * F('price')),
                amount_sum=Sum('amount'),
            )
            executed_quote = info['quote_cum']
            filled_amount = info['amount_sum'] or 0
            filled_price = executed_quote / filled_amount

            revenue.filled_amount = filled_amount
            revenue.coin_filled_price = filled_price / revenue.base_price

            if revenue.symbol.base_asset.symbol == Asset.IRT:
                user_quote = revenue.price * revenue.amount
                earning_quote = user_quote - executed_quote

                if revenue.side == SELL:
                    earning_quote = -earning_quote

                revenue.fiat_hedge_base = earning_quote

            revenue.save(update_fields=['filled_amount', 'coin_filled_price', 'fiat_hedge_base'])

        elif revenue.symbol == usdt_irt_symbol:
            revenue.coin_filled_price = 1
            revenue.filled_amount = revenue.amount
            revenue.save(update_fields=['filled_amount', 'coin_filled_price'])

        else:
            coin = revenue.symbol.asset.symbol

            if revenue.hedge_key:
                revenues = [*delegated_hedges[coin], revenue]
                delegated_hedges[coin] = []

                info = get_provider_requester().get_order(request_id=revenue.hedge_key)

                if info:
                    for r in revenues:
                        r.coin_filled_price = info['filled_price']
                        r.filled_amount = info['filled_amount']

                    TradeRevenue.objects.bulk_update(revenues, ['coin_filled_price', 'filled_amount'])
            else:
                delegated_hedges[coin].append(revenue)
