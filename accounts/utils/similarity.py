import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

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


NAME_SIMILARITY_THRESHOLD = 0.79


def name_similarity(name1, name2):
    name1, name2 = clean_persian_name(name1), clean_persian_name(name2)

    verified = str_similar_rate(name1, name2) >= NAME_SIMILARITY_THRESHOLD

    if not verified:
        verified = str_similar_rate(rotate_words(name1), name2) >= NAME_SIMILARITY_THRESHOLD

        if not verified:
            verified = str_similar_rate(rotate_words(name2), name1) >= NAME_SIMILARITY_THRESHOLD

    logger.info('verifying %s and %s is %s' % (name1, name2, verified))

    return verified
