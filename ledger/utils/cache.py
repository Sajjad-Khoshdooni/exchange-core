from cachetools import TTLCache
import hashlib
import logging

logger = logging.getLogger(__name__)


def get_cache_func_key(func, *args, **kwargs) -> str:
    serialise = [func.__module__, func.__name__]
    for arg in args:
        serialise.append(str(arg))

    for key, arg in kwargs.items():
        serialise.append(str(key))
        serialise.append(str(arg))

    key = hashlib.md5("".join(serialise).encode('utf-8')).hexdigest()

    return key


def ttl_cache(cache: TTLCache):
    def wrapper(func):
        def wrapped(*args, **kwargs):
            key = get_cache_func_key(func, *args, **kwargs)

            try:
                return cache[key]
            except KeyError:
                result = cache[key] = func(*args, **kwargs)

                return result

        return wrapped

    return wrapper

