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

    CoinMarketCap.objects.bulk_update(objects, fields=['change_24h', 'volume_24h'])
