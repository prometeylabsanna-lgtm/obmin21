"""Юридичні сторінки без стоп-слів і з режимом «лише обмін», і без нього."""

import os
import re
from unittest.mock import patch
from urllib.parse import urlparse

from django.core.cache import cache
from django.db import DatabaseError
from django.http import Http404
from django.urls import NoReverseMatch, get_resolver, reverse
from django.urls.resolvers import LocalePrefixPattern, URLResolver

from src.core.tests.eo_realdb import (
    RealDataTestCase,
    copy_real_db,
    normalize_path,
    prefixed_paths,
    restore_test_db,
    static_public_paths,
)
from src.core.tests.test_eo_spider import compile_stop_words, stop_word_hits

_KNOWN_LEGAL_PATHS = (
    '/publichna-oferta/',
    '/polityka-konfidentsiynosti/',
    '/polityka-cookie/',
)
_ROUTE_MARKERS = (
    'polityka',
    'oferta',
    'offer',
    'cookie',
    'privacy',
    'confidential',
    'legal',
    'terms',
)
_NAME_EXACT = frozenset({'privacy', 'offer', 'cookies', 'legal', 'terms'})
_CALLBACK_EXACT = frozenset({
    'privacy_page',
    'offer_page',
    'cookies_page',
    'legal_page',
    'terms_page',
})
_THEME_SLUGS = frozenset({'privacy', 'offer', 'cookies', 'legal', 'terms'})
_CLASS_MARKERS = ('privacy', 'cookie', 'oferta', 'polityka', 'legalpage', 'termspage', 'offerpage')
_VERBOSE_MARKERS = ('політик', 'оферт', 'cookie', 'конфіденц', 'юридич')
_SKIP_PREFIXES = ('admin/', 'static/', 'media/', 'tinymce/', 'htmx/', 'telegram/')
_SLUG_KEYS = ('slug', 'page_slug', 'document_slug')
_MODES = (
    (False, 'вимкнено'),
    (True, 'увімкнено'),
)
_CONVERTER = re.compile(r'<[^>]+>')


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


def legal_paths():
    """Відомі юридичні адреси плюс інші з urlpatterns і рядків бази."""
    slugs, stored = _database_legal()
    paths = list(_KNOWN_LEGAL_PATHS)
    paths.extend(path for path in static_public_paths() if _text_is_legal(path))
    paths.extend(_pattern_paths(slugs))
    paths.extend(_named_legal_paths(slugs))
    paths.extend(stored)
    cleaned = []
    for path in paths:
        pure = _as_path(path)
        if pure and '<' not in pure and '>' not in pure and not _skipped(pure):
            cleaned.append(pure)
    return _unique(cleaned)


class LegalPagesStopWordsTests(RealDataTestCase):
    def test_legal_pages_have_no_stop_words(self):
        try:
            from src.core.exchange_stopwords import STOP_WORDS
        except ImportError:
            STOP_WORDS = None
        if STOP_WORDS is None:
            self.fail('src.core.exchange_stopwords відсутній (гілка eo/filter не злита)')
        pattern = compile_stop_words(STOP_WORDS)
        urls = prefixed_paths(legal_paths())
        violations = []
        for enabled, label in _MODES:
            violations.extend(_scan(self.client, urls, pattern, enabled, label))
        if violations:
            self.fail('\n'.join(violations))


def _scan(client, urls, pattern, enabled, label):
    env = {'EXCHANGE_ONLY_MODE': '1' if enabled else '0'}
    found = []
    with patch.dict(os.environ, env):
        cache.clear()
        client.raise_request_exception = False
        for url in urls:
            response = client.get(url, follow=True)
            for line in stop_word_hits(url, response, pattern):
                found.append(f'{line} | {label}')
    return found


def _database_legal():
    from django.apps import apps
    from django.db import connection

    from src.core.theme import URL_THEME_MAP

    tables = set(connection.introspection.table_names())
    names_by_theme = {}
    for url_name, theme in URL_THEME_MAP.items():
        if theme in _THEME_SLUGS:
            names_by_theme.setdefault(theme, []).append(url_name)
    slugs = []
    paths = []
    for model in apps.get_models():
        if not _model_is_legal(model) or model._meta.db_table not in tables:
            continue
        try:
            if not model.objects.exists():
                continue
        except DatabaseError:
            continue
        theme = getattr(model, 'theme_slug', None)
        if theme in names_by_theme:
            for url_name in names_by_theme[theme]:
                paths.extend(_reverse_name(url_name, ()))
        slugs.extend(_model_slugs(model))
        paths.extend(_absolute_urls(model))
    return _unique(slugs), paths


def _model_is_legal(model):
    theme = str(getattr(model, 'theme_slug', '') or '').casefold()
    if theme in _THEME_SLUGS:
        return True
    name = model.__name__.casefold()
    if any(marker in name for marker in _CLASS_MARKERS):
        return True
    verbose = f'{model._meta.verbose_name} {model._meta.verbose_name_plural}'.casefold()
    return any(marker in verbose for marker in _VERBOSE_MARKERS)


def _model_slugs(model):
    if not any(field.name == 'slug' for field in model._meta.concrete_fields):
        return []
    try:
        values = model.objects.exclude(slug='').values_list('slug', flat=True)
    except DatabaseError:
        return []
    return [str(value).strip() for value in values if str(value or '').strip()]


def _absolute_urls(model):
    if not any(
        'get_absolute_url' in cls.__dict__ and not cls.__module__.startswith('django.')
        for cls in model.mro()
    ):
        return []
    try:
        objects = model.objects.all()
    except DatabaseError:
        return []
    found = []
    for obj in objects:
        try:
            url = obj.get_absolute_url()
        except (DatabaseError, Http404, NoReverseMatch):
            continue
        if url:
            found.append(str(url))
    return found


def _pattern_paths(slugs):
    paths = []
    for entry, route in _iter_patterns():
        if _skipped(route) or not _pattern_is_legal(entry, route):
            continue
        paths.extend(_concrete_routes(route, slugs))
    return paths


def _iter_patterns():
    def walk(patterns, prefix):
        for entry in patterns:
            pattern = entry.pattern
            if isinstance(pattern, LocalePrefixPattern):
                yield from walk(entry.url_patterns, prefix)
                continue
            route = f'{prefix}{pattern}'
            if isinstance(entry, URLResolver):
                yield from walk(entry.url_patterns, route)
                continue
            yield entry, route

    yield from walk(get_resolver().url_patterns, '')


def _pattern_is_legal(entry, route):
    if _text_is_legal(route):
        return True
    if _name_is_legal(entry.name or ''):
        return True
    callback = getattr(entry, 'callback', None)
    return callback is not None and _callback_is_legal(callback)


def _concrete_routes(route, slugs):
    if '<' not in route:
        return [normalize_path(route)]
    if len(_CONVERTER.findall(route)) != 1:
        return []
    paths = []
    for slug in slugs:
        filled = _CONVERTER.sub(lambda _match, value=slug: value, route, count=1)
        if '<' not in filled and not _skipped(filled):
            paths.append(normalize_path(filled))
    return paths


def _named_legal_paths(slugs):
    keys = [key for key in get_resolver().reverse_dict if isinstance(key, str)]
    paths = []
    for key in keys:
        if _name_is_legal(key):
            paths.extend(_reverse_name(key, slugs))
    return paths


def _reverse_name(name, slugs):
    try:
        return [reverse(name)]
    except NoReverseMatch:
        pass
    found = []
    for slug in slugs:
        for key in _SLUG_KEYS:
            try:
                found.append(reverse(name, kwargs={key: slug}))
            except NoReverseMatch:
                continue
            break
    return found


def _name_is_legal(name):
    tail = (name or '').rsplit(':', 1)[-1].casefold()
    if tail in _NAME_EXACT:
        return True
    return any(_marker_in_name(tail, marker) for marker in (
        'privacy',
        'cookie',
        'oferta',
        'polityka',
        'legal',
        'terms',
    ))


def _marker_in_name(name, marker):
    return (
        name == marker
        or name.startswith(f'{marker}_')
        or name.endswith(f'_{marker}')
        or f'_{marker}_' in name
    )


def _callback_is_legal(callback):
    view_class = getattr(callback, 'view_class', None)
    target = view_class or callback
    name = (getattr(target, '__name__', '') or '').casefold()
    if name in _CALLBACK_EXACT:
        return True
    return _marker_in_name(name, 'legal')


def _text_is_legal(value):
    folded = (value or '').casefold()
    return any(marker in folded for marker in _ROUTE_MARKERS)


def _skipped(path):
    cleaned = (path or '').lstrip('/')
    return any(
        cleaned == prefix.rstrip('/') or cleaned.startswith(prefix)
        for prefix in _SKIP_PREFIXES
    )


def _as_path(value):
    text = str(value or '').strip()
    if not text:
        return ''
    if '://' in text:
        parsed = urlparse(text)
        text = parsed.path or '/'
        if parsed.query:
            text = f'{text}?{parsed.query}'
    return normalize_path(text)


def _unique(paths):
    result = []
    seen = set()
    for path in paths:
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result
