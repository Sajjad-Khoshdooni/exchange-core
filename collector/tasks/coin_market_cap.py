import requests
from celery import shared_task

from collector.models import CoinMarketCap


@shared_task()
def update_coin_market_cap():
    coins = CoinMarketCap.request()
    id_to_coin = {c['id']: c for c in coins}

    objects = CoinMarketCap.objects.all()

    for obj in objects:
        data = id_to_coin.get(obj.internal_id)
        if data:
            price_info = data['quotes'][0]

            obj.change_24h = price_info['percentChange24h']
            obj.volume_24h = price_info['volume24h']
            obj.market_cap = price_info['marketCap']
            obj.change_1h = price_info['percentChange1h']
            obj.change_7d = price_info['percentChange7d']
            obj.high_24h = data['high24h']
            obj.low_24h = data['low24h']
            obj.cmc_rank = data['cmcRank']
            obj.circulating_supply = data['circulatingSupply']

    CoinMarketCap.objects.bulk_update(objects, fields=['change_24h', 'volume_24h', 'market_cap', 'change_1h',
                                                       'change_7d', 'high_24h', 'low_24h', 'cmc_rank',
                                                       'circulating_supply'])
