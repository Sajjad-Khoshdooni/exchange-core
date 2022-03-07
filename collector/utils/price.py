from redis import Redis

from django.conf import settings

price_redis = Redis.from_url(settings.PROVIDER_CACHE_LOCATION, charset="utf-8", decode_responses=True)
