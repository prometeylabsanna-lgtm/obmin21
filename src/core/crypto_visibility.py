import re

_STEMS = (
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
)
_TICKER = re.compile(
    r'(?<![0-9a-zа-яіїєґ])(btc|eth|usdt|usdc|bnb|sol|trx|ton)(?![0-9a-zа-яіїєґ])',
    re.IGNORECASE,
)
_LI = re.compile(r'<li\b[^>]*>.*?</li>', re.IGNORECASE | re.DOTALL)


def _show_crypto():
    from src.core.exchange_mode import exchange_only

    return not exchange_only()


def mentions_crypto(text):
    raw = str(text or '')
    if not raw.strip():
        return False
    low = raw.lower()
    if any(stem in low for stem in _STEMS):
        return True
    return _TICKER.search(low) is not None


def pair_is_crypto(pair):
    code = (getattr(pair, 'flag_code', '') or '').upper()
    if code in {'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'TRX', 'TON'}:
        return True
    return mentions_crypto(
        ' '.join(
            str(getattr(pair, name, '') or '')
            for name in ('code', 'name', 'slug', 'intro', 'seo_title', 'seo_description')
        )
    )


def visible_queryset(qs, *fields):
    if _show_crypto():
        return qs
    kept = []
    for obj in qs:
        parts = []
        for field in fields:
            value = obj
            for bit in field.split('__'):
                value = getattr(value, bit, '') if value is not None else ''
            parts.append(value)
        if not mentions_crypto(' '.join(str(part or '') for part in parts)):
            kept.append(obj.pk)
    return qs.filter(pk__in=kept)


def strip_crypto_items(html):
    if _show_crypto() or not html:
        return html

    def _drop(match):
        return '' if mentions_crypto(match.group(0)) else match.group(0)

    return _LI.sub(_drop, str(html))
