"""Приховані в режимі «лише обмін» адреси: 503/404 і sitemap."""

import os
from unittest.mock import patch

from django.core.cache import cache

from src.core.tests.eo_realdb import (
    HIDDEN_POST_SLUGS,
    VISIBLE_POST_SLUGS,
    RealDataTestCase,
    copy_real_db,
    hidden_paths,
    prefixed_paths,
    restore_test_db,
    retry_after_seconds,
    sitemap_paths,
)


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


def _mode(enabled, status=None):
    env = {'EXCHANGE_ONLY_MODE': '1' if enabled else '0'}
    if status is not None:
        env['HIDDEN_PAGE_STATUS'] = str(status)
    return patch.dict(os.environ, env)


class HiddenExchangePagesTests(RealDataTestCase):
    def test_known_hidden_targets_come_from_db(self):
        paths = set(hidden_paths())
        for slug in HIDDEN_POST_SLUGS:
            self.assertIn(f'/blog/{slug}/', paths)
        for slug in ('btc-usdt', 'eth-usdt', 'usdt-uah'):
            self.assertIn(f'/{slug}/', paths)
        for slug in ('kryptovalyuta', 'zoloto', 'perekazy'):
            self.assertIn(f'/blog/kategoriya/{slug}/', paths)
        for slug in VISIBLE_POST_SLUGS:
            self.assertNotIn(f'/blog/{slug}/', paths)
        self.assertNotIn('/blog/kategoriya/porady/', paths)
        self.assertNotIn('/blog/kategoriya/kurs-valyut/', paths)

    def test_hidden_pages_are_503_with_retry_after(self):
        with _mode(True, 503):
            cache.clear()
            expected = str(retry_after_seconds())
            problems = _status_problems(
                self.client,
                hidden_paths(),
                503,
                retry_after=expected,
            )
        self.assertFalse(problems, '\n'.join(problems))

    def test_hidden_pages_are_404_when_configured(self):
        with _mode(True, 404):
            cache.clear()
            problems = _status_problems(self.client, hidden_paths(), 404)
        self.assertFalse(problems, '\n'.join(problems))

    def test_hidden_pages_missing_from_sitemap_in_mode(self):
        with _mode(True, 503):
            cache.clear()
            locs = set(sitemap_paths(self.client))
            present = [url for url in prefixed_paths(hidden_paths()) if url in locs]
        self.assertFalse(present, 'Є у sitemap:\n' + '\n'.join(present))

    def test_hidden_pages_are_public_without_mode(self):
        with _mode(False):
            cache.clear()
            problems = _status_problems(self.client, hidden_paths(), 200)
            locs = set(sitemap_paths(self.client))
            for url in prefixed_paths(hidden_paths()):
                if url not in locs:
                    problems.append(f'{url} | sitemap | відсутній')
        self.assertFalse(problems, '\n'.join(problems))


def _status_problems(client, paths, status, retry_after=None):
    problems = []
    for url in prefixed_paths(paths):
        response = client.get(url)
        if response.status_code != status:
            problems.append(f'{url} | status | {response.status_code}')
            continue
        if retry_after is None:
            continue
        header = response.headers.get('Retry-After')
        if header != retry_after:
            problems.append(f'{url} | Retry-After | {header!r}')
    return problems
