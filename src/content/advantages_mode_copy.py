"""Порожні тексти режиму «Лише обмін» для сторінки переваг.

Повтор не перезаписує правки. Банер із монетами чи криптою не копіює.
"""

import re

from django.db.models import ImageField

from src.content.advantages_fields import (
    CMP_THEM_HTML_MODE,
    CMP_US_HTML_MODE,
    STAT_1_TEXT_MODE,
    advantage_default,
)
from src.core.exchange_stopwords import matches_stop_words

_TEXT_TYPES = frozenset({'CharField', 'TextField'})
_STAT_TEXT = frozenset({'stat_2_text', 'stat_3_text', 'stat_4_text'})
_STAT_NUMBER = re.compile(r'stat_\d+_number\Z')
_CLEAN_TEXT = {
    'cmp_us_html': CMP_US_HTML_MODE,
    'cmp_them_html': CMP_THEM_HTML_MODE,
}
_IMAGE_MARKERS = (
    'coin',
    'crypto',
    'bitcoin',
    'krypto',
    'tether',
    'usdt',
    'usdc',
    'крипт',
    'монет',
    'золот',
    'бітко',
    'битко',
    'gold',
)
_IMAGE_TICKERS = frozenset({'btc', 'eth', 'bnb', 'sol', 'trx', 'ton'})


def choose_mode_text(base_value, default, clean=''):
    """Копія чистого джерела або окремий чистий текст. Інакше порожньо."""
    base = str(base_value or '').strip()
    fallback = str(default or '').strip()
    source = base if base else fallback
    if source and not matches_stop_words(source):
        return source
    for candidate in (str(clean or '').strip(), fallback):
        if candidate and not matches_stop_words(candidate):
            return candidate
    return ''


def image_is_neutral(name):
    """Файл без монет і крипти. Порожнє ім’я нейтральним не є."""
    folded = str(name or '').replace('\\', '/').casefold().strip()
    if not folded:
        return False
    if any(marker in folded for marker in _IMAGE_MARKERS):
        return False
    stem = folded.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    tokens = [part for part in re.split(r'[^0-9a-zа-яіїєґ]+', stem) if part]
    return not any(token in _IMAGE_TICKERS for token in tokens)


def iter_mode_targets(model):
    for field in model._meta.fields:
        name = field.name
        if name.endswith('_mode'):
            continue
        kind = field.get_internal_type()
        if name in _STAT_TEXT or _STAT_NUMBER.fullmatch(name):
            yield name, 'text'
        elif name.startswith('why_') and kind in _TEXT_TYPES:
            yield name, 'text'
        elif isinstance(field, ImageField) and (
            name.startswith('why_banner') or name == 'why_coins'
        ):
            yield name, 'image'
        elif name.startswith('cmp_') and kind in _TEXT_TYPES:
            yield name, 'text'


def _fits(text, limit):
    if not text or matches_stop_words(text):
        return False
    return not limit or len(text) <= limit


def _blank(value):
    if value is None:
        return True
    if not isinstance(value, str):
        file_name = getattr(value, 'name', None)
        if file_name is not None:
            return not str(file_name).strip()
    return not str(value).strip()


def _file_name(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(getattr(value, 'name', '') or '').strip()


def fill_stat_1_text_mode(apps, schema_editor):
    """Ставить текст цифри 7K лише в порожнє поле. Повтор не перезаписує правки."""
    if not _fits(STAT_1_TEXT_MODE, None):
        return {}
    page_model = apps.get_model('content', 'AdvantagesPage')
    page = page_model.objects.filter(pk=1).first()
    if page is None:
        return {}
    names = {field.name for field in page_model._meta.fields}
    if 'stat_1_text_mode' not in names or not _blank(getattr(page, 'stat_1_text_mode', '')):
        return {}
    page_model.objects.filter(pk=page.pk).update(stat_1_text_mode=STAT_1_TEXT_MODE)
    return {'stat_1_text_mode': STAT_1_TEXT_MODE}


def fill_advantages_page_mode(apps, schema_editor):
    """Заповнює порожні поля режиму. Повтор не перезаписує правки."""
    stat_updates = fill_stat_1_text_mode(apps, schema_editor)
    page_model = apps.get_model('content', 'AdvantagesPage')
    page = page_model.objects.filter(pk=1).first()
    if page is None:
        return stat_updates
    names = {field.name for field in page_model._meta.fields}
    updates = {}
    for base, kind in iter_mode_targets(page_model):
        mode_name = f'{base}_mode'
        if mode_name not in names or not _blank(getattr(page, mode_name, '')):
            continue
        if kind == 'image':
            base_name = _file_name(getattr(page, base, ''))
            if image_is_neutral(base_name):
                updates[mode_name] = base_name
            continue
        default = advantage_default(base)
        clean = _CLEAN_TEXT.get(base, '')
        limit = getattr(page_model._meta.get_field(mode_name), 'max_length', None)
        text = choose_mode_text(getattr(page, base, ''), default, clean)
        if not _fits(text, limit):
            text = choose_mode_text('', default, clean)
        if not _fits(text, limit):
            continue
        updates[mode_name] = text
    if updates:
        page_model.objects.filter(pk=page.pk).update(**updates)
    if stat_updates:
        updates.update(stat_updates)
    return updates
