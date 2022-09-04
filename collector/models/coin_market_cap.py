from collections import defaultdict

from django.db import models
import requests


full_data_url = 'https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=4000&sortBy=rank&sortType=desc&convert=USD,BTC,ETH&cryptoType=all&tagType=all&audited=false&aux=ath,atl,high24h,low24h,num_market_pairs,cmc_rank,date_added,max_supply,circulating_supply,total_supply,volume_7d,volume_30d,self_reported_circulating_supply,self_reported_market_cap'
data_url = 'https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=4000&sortBy=rank&convert=USD&sortType=desc&cryptoType=all&tagType=all&audited=false&aux=high24h,low24h,cmc_rank,circulating_supply'


class CoinMarketCap(models.Model):

    SYMBOL_TRANSLATION = {
        'MIOTA': 'IOTA',
        'ELON': '1000ELON',
        'BABYDOGE': '1M-BABYDOGE',
        'FLOKI': '1000FLOKI',
        'QUACK': '1M-QUACK',
        'STARL': '1000STARL',
        'SAFEMARS': '1M-SAFEMARS',
    }

    symbol = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64)
    slug = models.CharField(max_length=64)
    internal_id = models.PositiveIntegerField()
    price = models.FloatField()
    market_cap = models.FloatField()
    change_1h = models.FloatField()
    change_24h = models.FloatField()
    volume_24h = models.FloatField()
    change_7d = models.FloatField()
    high_24h = models.FloatField()
    low_24h = models.FloatField()
    cmc_rank = models.IntegerField()
    circulating_supply = models.FloatField()

    @classmethod
    def request(cls):
        return requests.get(data_url).json()['data']['cryptoCurrencyList']

    @classmethod
    def fill(cls):
        coins = cls.request()
        # coins = list(filter(lambda x: x['quotes'][0]['marketCap'] > 0, coins))

        coins_per_symbol = defaultdict(list)

        existing_symbols = set(CoinMarketCap.objects.values_list('symbol', flat=True))

        for c in coins:
            symbol = c['symbol']

            if symbol not in existing_symbols:
                coins_per_symbol[symbol].append(c)

        objects = []

        for symbol, coins_list in coins_per_symbol.items():
            if len(coins_list) > 1:
                print('selecting %s between %d coins' % (symbol, len(coins_list)))

                coins_list.sort(key=lambda c: c['quotes'][0]['marketCap'], reverse=True)

                for c in coins_list:
                    print('  %s (cap = %s)' % (c['name'], c['quotes'][0]['marketCap']))

            coin = coins_list[0]

            price_info = coin['quotes'][0]

            objects.append(
                CoinMarketCap(
                    symbol=coin['symbol'],
                    name=coin['name'],
                    slug=coin['slug'],
                    internal_id=coin['id'],
                    price=price_info['price'],
                    market_cap=price_info['marketCap'],
                    change_1h=price_info.get('"percentChange1h', 0),
                    change_24h=price_info.get('percentChange24h', 0),
                    volume_24h=price_info.get('volume24h', 0),
                    change_7d=price_info.get('percentChange7d', 0),
                    high_24h=price_info.get('high24h', 0),
                    low_24h=price_info.get('low24h', 0),
                    cmc_rank=price_info.get('cmcRank', 0),
                    circulating_supply=price_info.get('circulatingSupply', 0),
                )
            )

        CoinMarketCap.objects.bulk_create(objects)
