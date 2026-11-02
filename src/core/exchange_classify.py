"""Тип пари і контенту для режиму «Лише обмін».

Авто = валютний обмін лишається видимим, крипто, метал, SWIFT і перекази — ні.
Ручні show/hide сильніші за цей тип.
"""

import re

PAIR_FIAT = 'fiat'
PAIR_CRYPTO = 'crypto'
PAIR_METAL = 'metal'
PAIR_OTHER = 'other'

CONTENT_CURRENCY = 'currency'
CONTENT_NON_EXCHANGE = 'non_exchange'
CONTENT_AUTO = 'auto'

VISIBILITY_AUTO = 'auto'
VISIBILITY_SHOW = 'show'
VISIBILITY_HIDE = 'hide'

FIAT_CODES = frozenset({
    'AED', 'AUD', 'BGN', 'BRL', 'BYN', 'CAD', 'CHF', 'CNY', 'CZK', 'DKK',
    'EUR', 'GBP', 'GEL', 'HKD', 'HUF', 'ILS', 'INR', 'JPY', 'KRW', 'KZT',
    'MDL', 'MXN', 'NOK', 'NZD', 'PLN', 'RON', 'SEK', 'SGD', 'THB', 'TRY',
    'UAH', 'USD', 'ZAR',
})
CRYPTO_CODES = frozenset({
    'ADA', 'APT', 'ATOM', 'AVAX', 'BCH', 'BNB', 'BTC', 'DAI', 'DOGE', 'DOT',
    'ETC', 'ETH', 'FIL', 'ICP', 'LINK', 'LTC', 'MATIC', 'NEAR', 'SHIB',
    'SOL', 'TON', 'TRX', 'UNI', 'USDC', 'USDT', 'XLM', 'XMR', 'XRP', 'ZEC',
})
METAL_CODES = frozenset({'GOLD', 'SILVER', 'XAG', 'XAU', 'XPD', 'XPT'})
_KNOWN_CODES = tuple(sorted(
    FIAT_CODES | CRYPTO_CODES | METAL_CODES,
    key=len,
    reverse=True,
))

_CRYPTO_STEMS = (
    'крипт', 'krypto', 'crypto', 'bitcoin', 'бітко', 'битко', 'ethereum',
    'ефіріум', 'етериум', 'ефір', 'tether', 'тезер', 'стейблко',
)
_NON_EXCHANGE_STEMS = _CRYPTO_STEMS + (
    'swift', 'переказ', 'perekaz', 'transfer', 'золот', 'zoloto', 'zolot',
    'gold', 'срібл', 'silver', 'зношен', 'znoshen',
)
_CURRENCY_STEMS = (
    'долар', 'євро', 'евро', 'валют', 'злотий', 'фунт', 'гривн',
    'dollar', 'euro', 'yevro', 'dolar', 'zlot', 'valyut',
)
_CURRENCY_CODES = (
    'usd', 'eur', 'pln', 'gbp', 'chf', 'uah', 'cny', 'jpy', 'czk', 'cad',
)
_NON_EXCHANGE_CODES = (
    'usdt', 'usdc', 'btc', 'eth', 'bnb', 'sol', 'trx', 'ton', 'xau', 'xag',
)
_LETTER = r'0-9a-zа-яіїєґ'
_CODE_RE = {}


def classify_pair_kind(code, name='', slug='', base_code=''):
    tokens = []
    for raw in (code, base_code, slug):
        tokens.extend(_pair_tokens(raw))
    blob = '\n'.join(str(part or '') for part in (code, name, slug)).casefold()
    if _has_metal(tokens, blob):
        return PAIR_METAL
    if _has_crypto(tokens, blob):
        return PAIR_CRYPTO
    if _has_stem(blob, _NON_EXCHANGE_STEMS) or _has_any_code(blob, _NON_EXCHANGE_CODES):
        return PAIR_OTHER
    if _all_fiat(tokens) or _has_stem(blob, _CURRENCY_STEMS):
        return PAIR_FIAT
    return PAIR_OTHER


def resolved_content_kind(*values):
    """currency або non_exchange. Невідомий текст лишається не-обмінним."""
    blob = '\n'.join(str(value or '') for value in values).casefold()
    if _has_stem(blob, _NON_EXCHANGE_STEMS) or _has_any_code(blob, _NON_EXCHANGE_CODES):
        return CONTENT_NON_EXCHANGE
    if _has_stem(blob, _CURRENCY_STEMS) or _has_any_code(blob, _CURRENCY_CODES):
        return CONTENT_CURRENCY
    return CONTENT_NON_EXCHANGE


def freeze_auto_kind(instance, field):
    """Поки стоїть auto — записує розрахований тип. Ручний тип не чіпає."""
    current = getattr(instance, field, '') or ''
    if current not in ('', CONTENT_AUTO):
        return ()
    if field == 'content_kind':
        resolved = _content_kind_for(instance)
    else:
        return ()
    if current == resolved:
        return ()
    setattr(instance, field, resolved)
    return (field,)


def assign_pair_exchange_fields(apps, schema_editor):
    pair = apps.get_model('rates', 'CurrencyPair')
    for row in pair.objects.all().iterator():
        pair.objects.filter(pk=row.pk).update(
            kind=classify_pair_kind(row.code, row.name, row.slug, row.base_code),
            exchange_visibility=(
                VISIBILITY_SHOW if row.exchange_safe else VISIBILITY_AUTO
            ),
        )


def assign_post_exchange_fields(apps, schema_editor):
    post = apps.get_model('blog', 'Post')
    category = apps.get_model('blog', 'Category')
    categories = {row.pk: row for row in category.objects.all()}
    for row in post.objects.all().iterator():
        cat = categories.get(row.category_id)
        texts = [row.title, row.slug, row.excerpt, row.seo_title]
        if cat is not None:
            texts.extend([cat.name, cat.slug])
        post.objects.filter(pk=row.pk).update(
            content_kind=resolved_content_kind(*texts),
            exchange_visibility=(
                VISIBILITY_SHOW if row.exchange_safe else VISIBILITY_AUTO
            ),
        )


def assign_service_exchange_fields(apps, schema_editor):
    service = apps.get_model('content', 'Service')
    for row in service.objects.all().iterator():
        service.objects.filter(pk=row.pk).update(
            content_kind=resolved_content_kind(
                row.title,
                row.slug,
                row.short_desc,
                row.seo_title,
                row.seo_description,
            ),
            exchange_visibility=(
                VISIBILITY_SHOW if row.exchange_safe else VISIBILITY_AUTO
            ),
        )


def assign_visibility_from_exchange_safe(apps, schema_editor, labels):
    for app_label, model_name in labels:
        model = apps.get_model(app_label, model_name)
        model.objects.filter(exchange_safe=True).update(
            exchange_visibility=VISIBILITY_SHOW,
        )


def noop_data_migration(apps, schema_editor):
    return None


def _content_kind_for(instance):
    texts = []
    for name in ('title', 'slug', 'excerpt', 'short_desc', 'seo_title', 'seo_description'):
        if hasattr(instance, name):
            texts.append(getattr(instance, name))
    category_id = getattr(instance, 'category_id', None)
    if category_id:
        category = instance.category
        texts.extend([category.name, category.slug])
    return resolved_content_kind(*texts)


def _pair_tokens(raw):
    tokens = []
    for part in re.findall(r'[A-Za-z]+', str(raw or '')):
        upper = part.upper()
        if upper in _KNOWN_LOOKUP:
            tokens.append(upper)
            continue
        consumed = _consume_all(upper)
        tokens.extend(consumed or (upper,))
    return tokens


def _consume_all(text):
    def walk(index):
        if index == len(text):
            return []
        for code in _KNOWN_CODES:
            if text.startswith(code, index):
                rest = walk(index + len(code))
                if rest is not None:
                    return [code, *rest]
        return None

    return walk(0)


def _all_fiat(tokens):
    meaningful = [token for token in tokens if token != 'UAH']
    if not meaningful:
        return 'UAH' in tokens
    return all(token in FIAT_CODES for token in meaningful)


def _has_metal(tokens, blob):
    if any(token in METAL_CODES for token in tokens):
        return True
    return _has_stem(blob, ('золот', 'zoloto', 'zolot', 'gold', 'срібл', 'silver'))


def _has_crypto(tokens, blob):
    if any(token in CRYPTO_CODES for token in tokens):
        return True
    return _has_stem(blob, _CRYPTO_STEMS) or _has_any_code(blob, _NON_EXCHANGE_CODES)


def _has_stem(blob, stems):
    return any(stem in blob for stem in stems)


def _has_any_code(blob, codes):
    return any(_has_code(blob, code) for code in codes)


def _has_code(blob, code):
    pattern = _CODE_RE.get(code)
    if pattern is None:
        pattern = re.compile(
            rf'(?<![{_LETTER}]){re.escape(code)}(?![{_LETTER}])',
        )
        _CODE_RE[code] = pattern
    return pattern.search(blob) is not None


_KNOWN_LOOKUP = FIAT_CODES | CRYPTO_CODES | METAL_CODES
