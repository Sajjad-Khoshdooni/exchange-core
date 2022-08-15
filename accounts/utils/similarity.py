import re
from difflib import SequenceMatcher

whitespace_regex = re.compile(r"\s+")


def clean_persian_name(name: str):
    mapping = {
        'ك': 'ک',
        'ي': 'ی',
        'أ': 'ا',
        'ۀ': 'ه',
        'ء': '',
        'ّ': '',
        'َ': '',
        'ِ': '',
        'ُ': '',
        'ً': '',
        'ٍ': '',
        'ٌ': '',
        'ْ': '',
        'ؤ': 'و',
        'ئ': 'ی',
        'إ': 'ا',
        'آ': 'ا',
        'ة': 'ه',
        'ٓ': '',
        'ٰ': '',
        'ٔ': '',
    }

    name = name.translate(str.maketrans(mapping)).strip()
    return whitespace_regex.sub(' ', name)


def str_similar_rate(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def rotate_words(s: str) -> str:
    parts = s.split(' ')
    rotated = parts[-1:] + parts[:-1]
    return ' '.join(rotated)
