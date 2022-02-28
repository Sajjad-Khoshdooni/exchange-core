import re
from difflib import SequenceMatcher

whitespace_regex = re.compile(r"\s+")


def clean_persian_name(name: str):
    name = name.replace('ك', 'ک').replace('ي', 'ی').strip()
    return whitespace_regex.sub(' ', name)


def str_similar_rate(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()
