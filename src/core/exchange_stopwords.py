"""Стоп-слова режиму «Лише обмін».

Видимість запису задає поле exchange_safe. У рубрики блогу такого поля немає:
у режимі її ховаємо, якщо назва або код містить одне з цих слів.
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
