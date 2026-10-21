"""Без env режиму обмін вимкнений: приховані й активні обмінні сторінки відкриті."""

import os
import sys
from contextlib import contextmanager
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client

from src.core.exchange_mode import is_exchange_only
from src.core.tests.eo_realdb import (
    RealDataTestCase,
    copy_real_db,
    exchange_paths,
    hidden_paths,
    inactive_pair_paths,
    prefixed_paths,
    restore_test_db,
)

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


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


def clear_exchange_caches():
    """django cache і lru_cache модулів режиму, sitemap і хрома."""
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
    from src.core.exchange_mode import hidden_page_status

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
    """Без EXCHANGE_ONLY_MODE і HIDDEN_PAGE_STATUS."""
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


class DefaultExchangeModeTests(RealDataTestCase):
    def test_mode_is_off_and_pages_are_open(self):
        inactive = set(inactive_pair_paths())
        hidden = [path for path in hidden_paths() if path not in inactive]
        exchange = [path for path in exchange_paths() if path not in inactive]
        with default_exchange_client() as client:
            client.raise_request_exception = False
            self.assertIsNone(os.environ.get(EXCHANGE_ONLY_ENV))
            self.assertIsNone(os.environ.get(HIDDEN_STATUS_ENV))
            self.assertFalse(is_exchange_only())
            problems = []
            problems.extend(_not_open(client, hidden, 'прихована'))
            problems.extend(_not_open(client, exchange, 'обмінна'))
        self.assertFalse(problems, '\n'.join(problems))


def _not_open(client, paths, kind):
    problems = []
    for url in prefixed_paths(paths):
        code = client.get(url).status_code
        if code != 200:
            problems.append(f'{url} | {kind} | {code}')
    return problems
