"""Порожні SEO-тексти готівкових пар. Криптопари лишаються порожніми."""

from src.core.exchange_stopwords import matches_stop_words

_CRYPTO_MARKERS = (
    'btc',
    'bitcoin',
    'бітко',
    'битко',
    'біткоїн',
    'eth',
    'ethereum',
    'ефір',
    'етериум',
    'ефіріум',
    'usdt',
    'usdc',
    'tether',
    'тезер',
    'bnb',
    'sol',
    'trx',
    'ton',
    'crypto',
    'крипт',
    'krypto',
    'стейблко',
)
_METAL_CODES = frozenset({'XAU', 'XAG', 'GOLD', 'SILVER'})


def _blank(value):
    return not str(value or '').strip()


def pair_blob(row):
    return '\n'.join((
        str(getattr(row, 'code', '') or ''),
        str(getattr(row, 'slug', '') or ''),
        str(getattr(row, 'name', '') or ''),
        str(getattr(row, 'base_code', '') or ''),
    )).casefold()


def is_crypto_pair(row):
    blob = pair_blob(row)
    if any(marker.casefold() in blob for marker in _CRYPTO_MARKERS):
        return True
    raw_codes = (
        str(getattr(row, 'code', '') or ''),
        str(getattr(row, 'base_code', '') or ''),
    )
    pieces = []
    for raw in raw_codes:
        pieces.extend(raw.replace('-', '/').split('/'))
    return any(piece.strip().upper() in _METAL_CODES for piece in pieces)


def fiat_pair_mode_copy(code):
    code = str(code or '').strip()
    return {
        'seo_title_mode': f'{code} — курс обміну готівки',
        'seo_description_mode': (
            f'Курс {code}: купівля та продаж готівки у відділеннях Обмін21.'
        ),
        'intro_mode': (
            f'Актуальний курс {code} до гривні у мережі Обмін21. '
            'На сторінці — купівля та продаж для обраного міста.\n\n'
            f'Як обміняти {code}\n\n'
            'Перегляньте курс, за потреби зафіксуйте його заявкою онлайн і '
            'приїдьте у зручне відділення з документом. Касир підтвердить '
            'умови та завершить операцію.\n\n'
            'Для великих сум радимо попередити відділення заздалегідь — '
            'так ми підготуємо потрібну готівку.'
        ),
    }


def fill_fiat_pair_mode(apps, schema_editor):
    """Заповнює порожні тексти готівкових пар. Повтор не перезаписує правки."""
    CurrencyPair = apps.get_model('rates', 'CurrencyPair')
    names = {field.name for field in CurrencyPair._meta.fields}
    if 'seo_title_mode' not in names:
        return
    for row in CurrencyPair.objects.all().order_by('pk'):
        code = str(row.code or '').strip()
        if not code or is_crypto_pair(row):
            continue
        updates = {}
        for name, text in fiat_pair_mode_copy(code).items():
            if name not in names or not _blank(getattr(row, name, '')):
                continue
            if matches_stop_words(text):
                continue
            updates[name] = text
        if updates:
            CurrencyPair.objects.filter(pk=row.pk).update(**updates)
