from difflib import SequenceMatcher


def str_similar_rate(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()
