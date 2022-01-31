from collections import defaultdict

from django.db import models
import requests


full_data_url = 'https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=10000&sortBy=rank&sortType=desc&convert=USD,BTC,ETH&cryptoType=all&tagType=all&audited=false&aux=ath,atl,high24h,low24h,num_market_pairs,cmc_rank,date_added,max_supply,circulating_supply,total_supply,volume_7d,volume_30d,self_reported_circulating_supply,self_reported_market_cap'
data_url = 'https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=10000&sortBy=rank&convert=USD&sortType=desc&cryptoType=all&tagType=all&audited=false'


class CoinMarketCap(models.Model):
    symbol = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64)
    slug = models.CharField(max_length=64)
    internal_id = models.PositiveIntegerField()
    price = models.FloatField()
    market_cap = models.FloatField()
    change_24h = models.FloatField()
    change_7d = models.FloatField()

    @classmethod
    def fill(cls):
        coins = requests.get(data_url).json()['data']['cryptoCurrencyList']
        coins = list(filter(lambda x: x['quotes'][0]['marketCap'] > 0, coins))

        coins_per_symbol = defaultdict(list)

        for c in coins:
            coins_per_symbol[c['symbol']].append(c)

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
                    change_24h=price_info['percentChange24h'],
                    change_7d=price_info['percentChange7d'],
                )
            )

        CoinMarketCap.objects.bulk_create(objects)
