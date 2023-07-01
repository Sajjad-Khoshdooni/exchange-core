import logging
from collections import defaultdict
from decimal import Decimal

from celery import shared_task
from django.db.models import Sum, F

from accounting.models import TradeRevenue
from ledger.models import Asset
from ledger.utils.market_maker import get_market_maker_requester
from ledger.utils.provider import get_provider_requester
from ledger.utils.trader import get_trader_requester
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
            revenue.gap_revenue = 0
            revenue.save(update_fields=['filled_amount', 'coin_filled_price', 'gap_revenue'])

        elif revenue.source == TradeRevenue.OTC_MARKET:
            info = Trade.objects.filter(order_id=int(revenue.hedge_key)).aggregate(
                quote_cum=Sum(F('amount') * F('price')),
                quote_cum_usdt=Sum(F('amount') * F('price') * F('base_usdt_price')),
                amount_sum=Sum('amount'),
            )

            filled_amount = info['amount_sum'] or 0

            revenue.filled_amount = filled_amount
            revenue.coin_filled_price = info['quote_cum_usdt'] / filled_amount
            revenue.gap_revenue = revenue.get_gap_revenue()

            if revenue.gap_revenue < 0:
                revenue.coin_price = revenue.coin_filled_price
                revenue.gap_revenue = revenue.get_gap_revenue()

            revenue.save(update_fields=['filled_amount', 'coin_filled_price', 'gap_revenue', 'coin_price'])

        elif revenue.symbol == usdt_irt_symbol:
            revenue.coin_filled_price = 1
            revenue.filled_amount = revenue.amount
            revenue.gap_revenue = revenue.get_gap_revenue()
            revenue.save(update_fields=['filled_amount', 'coin_filled_price', 'gap_revenue'])

        else:
            coin = revenue.symbol.asset.symbol

            if revenue.hedge_key and revenue.hedge_key.startswith('mm-'):
                info = get_market_maker_requester().get_trade_hedge_info(revenue.hedge_key.replace('mm-', ''))
                if info['real_revenue']:
                    revenue.gap_revenue = info['real_revenue']
                    revenue.filled_amount = info['amount']
                    revenue.coin_filled_price = info['hedge_price']
                    revenue.save(update_fields=['coin_filled_price', 'filled_amount', 'gap_revenue'])
            if revenue.hedge_key and revenue.hedge_key.startswith('tr-'):
                info = get_trader_requester().get_trade_hedge_info(revenue.hedge_key.replace('tr-', ''))
                if info['revenue']:
                    revenue.gap_revenue = info['revenue']
                    revenue.filled_amount = info['amount']
                    revenue.coin_filled_price = info['hedge_price']
                    revenue.save(update_fields=['coin_filled_price', 'filled_amount', 'gap_revenue'])
            elif revenue.hedge_key:
                revenues = [*delegated_hedges[coin], revenue]
                delegated_hedges[coin] = []

                info = get_provider_requester().get_order(request_id=revenue.hedge_key)

                if info and info['filled_amount']:
                    executed_amount = Decimal(info['filled_amount'])
                    executed_price = Decimal(info['filled_price'])

                    for r in revenues:
                        r.coin_filled_price = executed_price
                        r.filled_amount = min(r.amount, executed_amount)
                        r.gap_revenue = r.get_gap_revenue()

                        executed_amount -= r.filled_amount

                    TradeRevenue.objects.bulk_update(revenues, ['coin_filled_price', 'filled_amount', 'gap_revenue'])
            else:
                delegated_hedges[coin].append(revenue)
