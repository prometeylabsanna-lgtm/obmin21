"""Приховані в режимі «лише обмін» адреси: 503/404 і sitemap."""

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
from src.core.tests.test_eo_default_mode import forced_exchange_client


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


class HiddenExchangePagesTests(RealDataTestCase):
    def test_known_hidden_targets_come_from_db(self):
        paths = set(hidden_paths())
        for slug in HIDDEN_POST_SLUGS:
            self.assertIn(f'/blog/{slug}/', paths)
        for slug in ('btc-usdt', 'eth-usdt', 'usdt-uah', 'btc-uah'):
            self.assertIn(f'/{slug}/', paths)
        for slug in ('kryptovalyuta', 'zoloto', 'perekazy'):
            self.assertIn(f'/blog/kategoriya/{slug}/', paths)
        for slug in VISIBLE_POST_SLUGS:
            self.assertNotIn(f'/blog/{slug}/', paths)
        self.assertNotIn('/blog/kategoriya/porady/', paths)
        self.assertNotIn('/blog/kategoriya/kurs-valyut/', paths)

    def test_hidden_pages_are_503_with_retry_after(self):
        with forced_exchange_client(True, 503) as client:
            expected = str(retry_after_seconds())
            paths = [path for path in hidden_paths() if path != '/btc-uah/']
            problems = _status_problems(
                client,
                paths,
                503,
                retry_after=expected,
            )
            inactive = client.get('/btc-uah/')
            if inactive.status_code not in (404, 503):
                problems.append(f'/btc-uah/ | status | {inactive.status_code}')
            elif inactive.status_code == 503 and inactive.headers.get('Retry-After') != expected:
                problems.append(
                    f'/btc-uah/ | Retry-After | {inactive.headers.get("Retry-After")!r}',
                )
        self.assertFalse(problems, '\n'.join(problems))

    def test_hidden_pages_are_404_when_configured(self):
        with forced_exchange_client(True, 404) as client:
            problems = _status_problems(client, hidden_paths(), 404)
        self.assertFalse(problems, '\n'.join(problems))

    def test_hidden_pages_missing_from_sitemap_in_mode(self):
        with forced_exchange_client(True, 503) as client:
            locs = set(sitemap_paths(client))
            present = [url for url in prefixed_paths(hidden_paths()) if url in locs]
        self.assertFalse(present, 'Є у sitemap:\n' + '\n'.join(present))

    def test_hidden_pages_are_public_without_mode(self):
        paths = [path for path in hidden_paths() if path != '/btc-uah/']
        with forced_exchange_client(False) as client:
            problems = _status_problems(client, paths, 200)
            locs = set(sitemap_paths(client))
            for url in prefixed_paths(paths):
                if '/blog/kategoriya/' in url:
                    continue
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
