from tronpy.providers import HTTPProvider
from tronpy import Tron

_tron = None


def get_tron_client() -> Tron:
    global _tron
    if _tron is None:
        provider = HTTPProvider(api_key='d69566b0-4604-49b5-8066-d7441b3210ff')
        _tron = Tron(provider=provider)
    return _tron
