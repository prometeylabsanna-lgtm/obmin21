import re

_LETTER = r'A-Za-z\u0400-\u04FF'
_STOP_RE = re.compile(
    rf'(?iu)(?<![{_LETTER}])(?:'
    r'крипт\w*'
    r'|crypto\w*'
    r'|usdt'
    r'|btc'
    r'|swift'
    r'|переказ\w*'
    r'|перевод\w*'
    r'|золот\w*'
    r'|зношен\w*'
    r'|изношен\w*'
    r'|опт(?!им|ич|ик)\w*'
    rf')(?![{_LETTER}])',
)
_SPLIT_PUNCT_RE = re.compile(r'\s+(?:/|[-–—|])\s*|\s*(?:/|[-–—|])\s+')
_SPACE_BEFORE_PUNCT_RE = re.compile(r'\s+([,.;:!?])')
_MULTI_SPACE_RE = re.compile(r'\s{2,}')
_EDGE_RE = re.compile(r'^[\s,.;:/|\-–—]+|[\s,.;:/|\-–—]+$')


def contains_stop_word(text):
    if not text:
        return False
    return _STOP_RE.search(str(text)) is not None


def strip_stop_words(text):
    raw = str(text or '')
    cleaned, count = _STOP_RE.subn(' ', raw)
    if not count:
        return raw
    cleaned = cleaned.replace('\r', ' ').replace('\n', ' ')
    cleaned = _SPLIT_PUNCT_RE.sub(' ', cleaned)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r'\1', cleaned)
    cleaned = _MULTI_SPACE_RE.sub(' ', cleaned)
    cleaned = _EDGE_RE.sub('', cleaned)
    return _MULTI_SPACE_RE.sub(' ', cleaned).strip()
