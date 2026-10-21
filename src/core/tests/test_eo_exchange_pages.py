"""Сторінки обміну лишаються 200 і з увімкненим режимом, і без нього."""

from src.core.tests.eo_realdb import (
    VISIBLE_POST_SLUGS,
    RealDataTestCase,
    classify_eur_usd,
    copy_real_db,
    exchange_paths,
    forced_exchange_client,
    inactive_pair_paths,
    prefixed_paths,
    restore_test_db,
)


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


class ExchangePagesStayTests(RealDataTestCase):
    def test_known_exchange_targets_come_from_db(self):
        paths = set(exchange_paths())
        for path in (
            '/',
            '/kursy/',
            '/posluhy/',
            '/perevahy/',
            '/faq/',
            '/blog/',
            '/vidhuky/',
            '/kontakty/',
            '/mista/',
            '/mista/kyiv/',
            '/polityka-konfidentsiynosti/',
            '/publichna-oferta/',
            '/polityka-cookie/',
            '/sitemap.xml',
            '/robots.txt',
            '/usd-uah/',
            '/eur-uah/',
            '/pln-uah/',
            '/eur-usd/',
            '/blog/kategoriya/kurs-valyut/',
            '/blog/kategoriya/zaoshchadzhennya/',
            '/blog/kategoriya/porady/',
        ):
            self.assertIn(path, paths, path)
        for slug in VISIBLE_POST_SLUGS:
            self.assertIn(f'/blog/{slug}/', paths)
        self.assertNotIn('/blog/kategoriya/zoloto/', paths)
        self.assertNotIn('/btc-usdt/', paths)
        self.assertNotIn('/btc-uah/', paths)
        _kind, why = classify_eur_usd()
        print(why)
        self.assertEqual(_kind, 'exchange', why)

    def test_exchange_pages_ok_in_mode(self):
        self._assert_ok(True)

    def test_exchange_pages_ok_without_mode(self):
        self._assert_ok(False)

    def _assert_ok(self, enabled):
        inactive = set(inactive_pair_paths())
        paths = [path for path in exchange_paths() if path not in inactive]
        with forced_exchange_client(enabled) as client:
            problems = []
            for url in prefixed_paths(paths):
                response = client.get(url)
                if response.status_code != 200:
                    problems.append(f'{url} | status | {response.status_code}')
        self.assertFalse(problems, '\n'.join(problems))
