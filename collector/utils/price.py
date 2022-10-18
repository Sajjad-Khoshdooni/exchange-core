from redis import Redis

from django.conf import settings

price_redis = Redis.from_url(settings.PRICE_CACHE_LOCATION, decode_responses=True)
