"""Спільна опора EO-тестів: копія реальної бази і публічні адреси.

Оригінальний db.sqlite3 тести не відкривають на запис. HTTP-тести ходять
у тимчасову копію, перевірка міграцій — окремим зʼєднанням mode=ro.
"""

import os
import re
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used
from django.core.cache import cache
from django.db import connection, connections
from django.test import Client, TestCase
from django.urls import get_resolver
from django.urls.resolvers import LocalePrefixPattern, URLResolver

HIDDEN_POST_SLUGS = (
    'kryptovalyuta-btc-usdt',
    'investytsiyne-zoloto',
    'mizhnarodni-perekazy',
    'znosheni-kupyury',
)
VISIBLE_POST_SLUGS = (
    'kurs-dolara-2027',
    'dolar-chy-yevro',
    'spravzhnya-kupyura',
    'kurs-kupivli-prodazhu',
    'fiksatsiya-kursu-onlain',
    'bezpechno-velyka-suma',
)
FIAT_CODES = ('USD', 'EUR', 'PLN')
CRYPTO_CODES = frozenset({'BTC', 'ETH', 'USDT'})
EXPLICIT_HIDDEN_PAIR_SLUGS = ('btc-uah',)
CLASSIFIED_PAIR_SLUG = 'eur-usd'
EXCHANGE_STATIC_PATHS = (
    '/',
    '/kursy/',
    '/posluhy/',
    '/perevahy/',
    '/faq/',
    '/blog/',
    '/vidhuky/',
    '/kontakty/',
    '/mista/',
    '/polityka-konfidentsiynosti/',
    '/publichna-oferta/',
    '/polityka-cookie/',
    '/sitemap.xml',
    '/robots.txt',
)
_LITERAL_ROUTE = re.compile(r'^[A-Za-z0-9._~/-]*$')
_SKIP_PREFIXES = ('admin/', 'static/', 'media/')
_STATE = {}
EXCHANGE_ONLY_ENV = 'EXCHANGE_ONLY_MODE'
HIDDEN_STATUS_ENV = 'HIDDEN_PAGE_STATUS'
_CACHE_PREFIXES = (
    'src.core.',
    'src.blog.',
    'src.rates.',
    'src.reviews.',
    'src.network.',
    'src.content.',
    'django.contrib.sitemaps',
)


def real_db_path():
    return (Path(settings.BASE_DIR) / 'db.sqlite3').resolve()


def real_db_uri():
    return f'file:{real_db_path().as_posix()}?mode=ro'


def copy_real_db():
    """Підміняє тестову sqlite копією реальної бази. Оригінал лише читається."""
    if _STATE.get('active'):
        return
    source = real_db_path()
    if not source.is_file():
        raise RuntimeError(f'Немає файлу бази {source}')
    handle, raw_name = tempfile.mkstemp(prefix='obmin21_eo_', suffix='.sqlite3')
    os.close(handle)
    dest = Path(raw_name)
    try:
        _backup_readonly(source, dest)
        _swap_default(source, dest)
        _assert_copy_is_not_original(source)
    except Exception:
        restore_test_db()
        raise


def restore_test_db():
    if not _STATE.get('active'):
        return
    dest = _STATE.get('dest')
    conn = connections['default']
    conn.close()
    previous = _STATE.get('conn_name')
    if previous is not None:
        conn.settings_dict['NAME'] = previous
    settings_name = _STATE.get('settings_name')
    if settings_name is not None:
        settings.DATABASES['default']['NAME'] = settings_name
    _STATE.clear()
    if dest is not None:
        dest.unlink(missing_ok=True)


def _backup_readonly(source, dest):
    src = sqlite3.connect(f'file:{source.as_posix()}?mode=ro', uri=True)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _swap_default(source, dest):
    conn = connections['default']
    _STATE['conn_name'] = conn.settings_dict['NAME']
    _STATE['settings_name'] = settings.DATABASES['default']['NAME']
    _STATE['dest'] = dest
    _STATE['source'] = source
    _STATE['active'] = True
    uri = f'file:{dest.resolve().as_posix()}?mode=rwc'
    conn.settings_dict['NAME'] = uri
    settings.DATABASES['default']['NAME'] = uri
    conn.close()


def _assert_copy_is_not_original(source):
    from src.blog.models import Post

    with connection.cursor() as cursor:
        cursor.execute('PRAGMA database_list')
        opened = [row[2] for row in cursor.fetchall()]
    for item in opened:
        if item and Path(item).resolve() == source:
            raise RuntimeError('Тести відкрили оригінальну db.sqlite3')
    if not Post.objects.filter(slug='kurs-dolara-2027', status='published').exists():
        raise RuntimeError('Копія бази без опублікованої статті kurs-dolara-2027')


def clear_exchange_caches():
    """django cache і lru_cache модулів режиму, sitemap і хрома.

    Атрибути запиту _exchange_only і _hidden_page_status жиють лише на request.
    Їх знімає новий Client: middleware і context processor збираються заново.
    """
    cache.clear()
    for name, module in list(sys.modules.items()):
        if module is None or not name.startswith(_CACHE_PREFIXES):
            continue
        for obj in list(vars(module).values()):
            owner = getattr(obj, '__module__', '') or ''
            clear = getattr(obj, 'cache_clear', None)
            info = getattr(obj, 'cache_info', None)
            if owner.startswith(_CACHE_PREFIXES) and callable(clear) and callable(info):
                clear()


def _require_forced_mode(enabled, status):
    from src.core.exchange_mode import hidden_page_status, is_exchange_only

    actual = is_exchange_only()
    if actual != enabled:
        raise AssertionError(
            f'{EXCHANGE_ONLY_ENV}={os.environ.get(EXCHANGE_ONLY_ENV)!r} '
            f'але is_exchange_only()={actual}'
        )
    if status is None:
        return
    actual_status = hidden_page_status()
    if actual_status != status:
        raise AssertionError(
            f'{HIDDEN_STATUS_ENV}={os.environ.get(HIDDEN_STATUS_ENV)!r} '
            f'але hidden_page_status()={actual_status}'
        )


@contextmanager
def forced_exchange_client(enabled, status=None):
    """Примусовий режим через env. Новий Client після скидання кешів."""
    env = {EXCHANGE_ONLY_ENV: '1' if enabled else '0'}
    if status is not None:
        status = int(status)
        env[HIDDEN_STATUS_ENV] = str(status)
    with patch.dict(os.environ, env):
        clear_exchange_caches()
        client = Client()
        try:
            _require_forced_mode(bool(enabled), status)
            yield client
        finally:
            clear_exchange_caches()


@contextmanager
def default_exchange_client():
    """Без EXCHANGE_ONLY_MODE і HIDDEN_PAGE_STATUS: лишається SiteSettings."""
    kept = {
        key: value
        for key, value in os.environ.items()
        if key not in (EXCHANGE_ONLY_ENV, HIDDEN_STATUS_ENV)
    }
    with patch.dict(os.environ, kept, clear=True):
        clear_exchange_caches()
        client = Client()
        try:
            yield client
        finally:
            clear_exchange_caches()


class RealDataTestCase(TestCase):
    def setUp(self):
        super().setUp()
        clear_exchange_caches()


def language_prefixes():
    """Префікси мов так, як їх віддає URLconf проєкту."""
    used, prefix_default = is_language_prefix_patterns_used(settings.ROOT_URLCONF)
    rows = []
    for code, _label in settings.LANGUAGES:
        if used and (prefix_default or code != settings.LANGUAGE_CODE):
            rows.append((code, f'/{code}'))
        else:
            rows.append((code, ''))
    return rows


def _split_query(path):
    if '?' in path:
        pure, query = path.split('?', 1)
        return pure, f'?{query}'
    return path, ''


def normalize_path(path):
    pure, query = _split_query(path or '/')
    if not pure.startswith('/'):
        pure = f'/{pure}'
    pure = re.sub(r'/{2,}', '/', pure)
    return f'{pure}{query}'


def prefix_path(prefix, path):
    pure, query = _split_query(normalize_path(path))
    if prefix:
        base = '/' + prefix.strip('/')
        pure = f'{base}/' if pure == '/' else f'{base}{pure}'
    return f'{pure}{query}'


def strip_language_prefix(path, prefix):
    pure, query = _split_query(normalize_path(path))
    if prefix:
        base = '/' + prefix.strip('/')
        if pure == base or pure == f'{base}/':
            pure = '/'
        elif pure.startswith(f'{base}/'):
            pure = pure[len(base):] or '/'
    return f'{pure}{query}'


def prefixed_paths(paths):
    result = []
    seen = set()
    for _code, prefix in language_prefixes():
        for path in paths:
            url = prefix_path(prefix, path)
            if url not in seen:
                seen.add(url)
                result.append(url)
    return result


def _skipped_route(route):
    cleaned = route.lstrip('/')
    return any(cleaned == prefix.rstrip('/') or cleaned.startswith(prefix) for prefix in _SKIP_PREFIXES)


def static_public_paths():
    """Літеральні маршрути з urlpatterns, без admin і без параметрів."""
    found = []
    seen = set()

    def walk(patterns, prefix):
        for entry in patterns:
            pattern = entry.pattern
            if isinstance(pattern, LocalePrefixPattern):
                walk(entry.url_patterns, prefix)
                continue
            route = str(pattern)
            if not _LITERAL_ROUTE.fullmatch(route):
                continue
            full = f'{prefix}{route}'
            if _skipped_route(full):
                continue
            if isinstance(entry, URLResolver):
                walk(entry.url_patterns, full)
                continue
            path = normalize_path(full)
            if path not in seen:
                seen.add(path)
                found.append(path)

    walk(get_resolver().url_patterns, '')
    return found


def sitemap_paths(client, prefix=''):
    response = client.get(prefix_path(prefix, '/sitemap.xml'))
    if response.status_code != 200:
        return []
    root = ElementTree.fromstring(response.content)
    paths = []
    for node in root.iter():
        if not node.tag.endswith('loc') or not (node.text and node.text.strip()):
            continue
        parsed = urlparse(node.text.strip())
        path = parsed.path or '/'
        if parsed.query:
            path = f'{path}?{parsed.query}'
        paths.append(strip_language_prefix(path, prefix))
    return paths


def homepage_links(client, prefix=''):
    from html.parser import HTMLParser

    class _Hrefs(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.hrefs = []

        def handle_starttag(self, tag, attrs):
            if tag.lower() != 'a':
                return
            for key, value in attrs:
                if key.lower() == 'href' and value:
                    self.hrefs.append(value.strip())

    page = prefix_path(prefix, '/')
    response = client.get(page, follow=True)
    if response.status_code != 200:
        return []
    parser = _Hrefs()
    parser.feed(response.content.decode(response.charset, errors='replace'))
    parser.close()
    base = response.wsgi_request.build_absolute_uri(page)
    host = (response.wsgi_request.get_host() or '').split(':')[0].lower()
    allowed_hosts = {'', 'testserver', 'localhost', '127.0.0.1', host}
    paths = []
    for href in parser.hrefs:
        lowered = href.lower()
        if not href or lowered.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue
        parsed = urlparse(urljoin(base, href))
        if parsed.scheme not in ('', 'http', 'https'):
            continue
        link_host = (parsed.hostname or '').lower()
        if link_host not in allowed_hosts:
            continue
        path = parsed.path or '/'
        if _skipped_route(path):
            continue
        if parsed.query:
            path = f'{path}?{parsed.query}'
        paths.append(strip_language_prefix(path, prefix))
    return paths


def discover_public_paths(client, prefix=''):
    found = []
    seen = set()
    chunks = (
        static_public_paths(),
        sitemap_paths(client, prefix),
        homepage_links(client, prefix),
    )
    for chunk in chunks:
        for path in chunk:
            url = prefix_path(prefix, strip_language_prefix(path, prefix))
            if url in seen:
                continue
            seen.add(url)
            found.append(url)
    return sorted(found)


def _code_tokens(code):
    return {part.upper() for part in re.findall(r'[A-Za-z0-9]+', code or '')}


def post_is_exchange_visible(post):
    return (post.slug or '') not in HIDDEN_POST_SLUGS


def _unique(paths):
    result = []
    seen = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result


def _pair_by_slug(slug):
    from src.rates.models import CurrencyPair

    return CurrencyPair.objects.filter(slug=slug).first()


def classify_eur_usd():
    """Фіат (не pair_is_crypto) — обмінна; крипто — прихована."""
    from src.core.crypto_visibility import pair_is_crypto

    pair = _pair_by_slug(CLASSIFIED_PAIR_SLUG)
    if pair is None:
        return 'missing', 'eur-usd: немає CurrencyPair у базі'
    crypto = pair_is_crypto(pair)
    flag = (pair.flag_code or '').upper()
    safe = bool(pair.exchange_safe)
    active = bool(pair.is_active)
    if crypto:
        return 'hidden', (
            'eur-usd: прихована. '
            f'pair_is_crypto=True, flag_code={flag}, code={pair.code}, '
            f'name={pair.name}, exchange_safe={safe}, is_active={active}'
        )
    return 'exchange', (
        'eur-usd: обмінна (фіат). '
        f'pair_is_crypto=False: flag_code={flag} не крипто-тикер; '
        f'code={pair.code}, name={pair.name}, slug={pair.slug}; '
        'intro і seo без крипто-стемів. '
        f'exchange_safe={safe} клас не змінює: pair_detail і get_active_pairs '
        'ховають пару лише через pair_is_crypto, не через ExchangeVisibleQuerySet. '
        f'is_active={active}.'
    )


def explicit_hidden_pair_paths():
    paths = [f'/{slug}/' for slug in EXPLICIT_HIDDEN_PAIR_SLUGS]
    kind, _why = classify_eur_usd()
    if kind == 'hidden':
        paths.append(f'/{CLASSIFIED_PAIR_SLUG}/')
    return paths


def explicit_exchange_pair_paths():
    kind, _why = classify_eur_usd()
    if kind == 'exchange':
        return [f'/{CLASSIFIED_PAIR_SLUG}/']
    return []


def inactive_pair_paths():
    from src.rates.models import CurrencyPair

    slugs = (
        CurrencyPair.objects.filter(is_active=False)
        .exclude(slug='')
        .values_list('slug', flat=True)
    )
    return [f'/{slug}/' for slug in slugs]


def spider_extra_paths():
    """Активна фіатна пара поза sitemap: павук має зайти на неї сам."""
    inactive = set(inactive_pair_paths())
    return [path for path in explicit_exchange_pair_paths() if path not in inactive]


def _published_posts():
    from src.blog.models import Post

    return Post.objects.filter(status=Post.Status.PUBLISHED).select_related('category')


def crypto_pair_paths():
    from src.rates.models import CurrencyPair

    paths = []
    pairs = CurrencyPair.objects.filter(is_active=True).exclude(slug='')
    for pair in pairs:
        if _code_tokens(pair.code) & CRYPTO_CODES:
            paths.append(f'/{pair.slug}/')
    return paths


def fiat_pair_paths():
    from src.rates.models import CurrencyPair

    paths = []
    pairs = (
        CurrencyPair.objects.filter(is_active=True, code__in=FIAT_CODES)
        .exclude(slug='')
        .order_by('sort_order', 'code')
    )
    for pair in pairs:
        paths.append(f'/{pair.slug}/')
    return paths


def city_paths():
    from src.network.models import City

    slugs = (
        City.objects.filter(is_active=True)
        .exclude(slug='')
        .order_by('sort_order', 'name')
        .values_list('slug', flat=True)
    )
    return [f'/mista/{slug}/' for slug in slugs]


def _rubric_groups():
    from src.blog.models import Category

    visible = set()
    occupied = set()
    for post in _published_posts():
        occupied.add(post.category_id)
        if post_is_exchange_visible(post):
            visible.add(post.category_id)
    hidden = []
    shown = []
    categories = Category.objects.filter(show_in_filter=True).exclude(slug='').order_by('sort_order', 'name')
    for category in categories:
        path = f'/blog/kategoriya/{category.slug}/'
        if category.id in occupied and category.id not in visible:
            hidden.append(path)
        elif category.id in visible:
            shown.append(path)
    return hidden, shown


def hidden_paths():
    posts = [f'/blog/{slug}/' for slug in HIDDEN_POST_SLUGS]
    rubrics, _shown = _rubric_groups()
    return _unique(posts + crypto_pair_paths() + rubrics + explicit_hidden_pair_paths())


def exchange_paths():
    _hidden, rubrics = _rubric_groups()
    posts = [f'/blog/{slug}/' for slug in VISIBLE_POST_SLUGS]
    return _unique(
        list(EXCHANGE_STATIC_PATHS)
        + city_paths()
        + fiat_pair_paths()
        + explicit_exchange_pair_paths()
        + posts
        + rubrics
    )


def retry_after_seconds():
    from src.core.models import SiteSettings

    seconds = (
        SiteSettings.objects.filter(pk=1)
        .values_list('retry_after_seconds', flat=True)
        .first()
    )
    return int(seconds if seconds is not None else 86400)
