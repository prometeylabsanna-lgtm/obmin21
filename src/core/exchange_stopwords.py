"""Стоп-слова режиму «Лише обмін».

Джерело копії:
/Users/olegbonislavskyi/Sites/Obmin21-wt-filter/src/core/exchange_stopwords.py
У гілці eo/cms модуля могло не бути. Якщо імпорт звідти не вдасться,
той самий список лежить запасним варіантом у exchange_preview.py.
"""

STOP_WORDS = (
    'крипт',
    'krypto',
    'crypto',
    'bitcoin',
    'бітко',
    'битко',
    'ethereum',
    'ефіріум',
    'етериум',
    'usdt',
    'usdc',
    'tether',
    'тезер',
    'стейблко',
    'btc',
    'eth',
    'bnb',
    'sol',
    'trx',
    'ton',
    'біткоїн',
    'swift',
    'переказ',
    'transfer',
    'золот',
    'gold',
    'оптов',
    'зношен',
    'електронн валют',
)


def matches_stop_words(*values):
    parts = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text.casefold())
    if not parts:
        return False
    blob = '\n'.join(parts)
    return any(word.casefold() in blob for word in STOP_WORDS)
