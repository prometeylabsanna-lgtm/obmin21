"""Режим без env береться з SiteSettings копії бази.

План не визначає режим за замовчуванням.
"""

import os

from src.core.exchange_mode import hidden_page_status, is_exchange_only
from src.core.tests.eo_realdb import (
    EXCHANGE_ONLY_ENV,
    HIDDEN_STATUS_ENV,
    RealDataTestCase,
    copy_real_db,
    default_exchange_client,
    exchange_paths,
    hidden_paths,
    inactive_pair_paths,
    prefixed_paths,
    restore_test_db,
)

_NOTE = 'План не визначає режим за замовчуванням'


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


class DefaultExchangeModeTests(RealDataTestCase):
    def test_pages_match_sitesettings_mode(self):
        inactive = set(inactive_pair_paths())
        exchange = [path for path in exchange_paths() if path not in inactive]
        hidden = list(hidden_paths())
        hidden_open = [
            path for path in hidden
            if path not in inactive and path != '/btc-uah/'
        ]
        with default_exchange_client() as client:
            self.assertIsNone(os.environ.get(EXCHANGE_ONLY_ENV))
            self.assertIsNone(os.environ.get(HIDDEN_STATUS_ENV))
            enabled = is_exchange_only()
            status = hidden_page_status()
            hidden_codes = _codes(client, hidden)
            exchange_codes = _codes(client, exchange)

        lines = [
            _NOTE,
            f'is_exchange_only()={enabled}',
            f'hidden_page_status()={status}',
            'приховані:',
        ]
        lines.extend(f'{url} {code}' for url, code in hidden_codes)
        lines.append('обмінні:')
        lines.extend(f'{url} {code}' for url, code in exchange_codes)
        print('\n'.join(lines))

        by_url = dict(hidden_codes)
        by_url.update(exchange_codes)
        problems = []
        if enabled:
            for url in prefixed_paths(exchange):
                code = by_url[url]
                if code != 200:
                    problems.append(f'{url} | обмінна | {code}')
            for url in prefixed_paths(hidden):
                code = by_url[url]
                if code not in (503, 404):
                    problems.append(f'{url} | прихована | {code}')
        else:
            for url in prefixed_paths(hidden_open + exchange):
                code = by_url[url]
                if code != 200:
                    problems.append(f'{url} | {code}')
        self.assertFalse(problems, _NOTE + '\n' + '\n'.join(problems))


def _codes(client, paths):
    rows = []
    for url in prefixed_paths(paths):
        rows.append((url, client.get(url).status_code))
    return rows
