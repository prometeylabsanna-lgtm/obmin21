import os
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_PHRASES = (
    'Оновлення курсу через',
    'Оновлено сьогодні',
    '30 хв',
)
_TIMER_ATTRS = (
    'data-bk-timer',
    'data-rate-timer',
    'data-rate-refresh',
    'data-countdown',
    'data-hold-timer',
    'data-update-timer',
)
_JS_STARTS = _TIMER_ATTRS + (
    'setInterval(tick',
    'expiresAt',
    '30 * 60 * 1000',
    'Оновлення курсу через',
)


class NoRateTimersTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)
        city = City.objects.create(
            name='Київ',
            slug='kyiv',
            phone='+380441112233',
            sort_order=0,
        )
        Branch.objects.create(
            city=city,
            address='Київ, вул. 1',
            phone=city.phone,
        )
        pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
            exchange_safe=True,
        )
        Quote.objects.create(
            pair=pair,
            board=RateBoard.RETAIL,
            city=city,
            buy=Decimal('41.20'),
            sell=Decimal('41.80'),
        )
        page = HomePage.load()
        page.calc_lock = 'Оновлення курсу через 05:00. Курс діє 30 хв'
        page.save(update_fields=['calc_lock'])

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def _html(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def _assert_clean(self, html, label):
        for phrase in _PHRASES:
            self.assertNotIn(phrase, html, '%s: %s' % (label, phrase))
        for attr in _TIMER_ATTRS:
            self.assertNotIn(attr, html, '%s: %s' % (label, attr))

    def test_pages_have_no_rate_update_copy_or_timer_attrs(self):
        pages = (
            ('home', reverse('core:home'), 'data-qa="home-calc"'),
            ('rates', reverse('rates:rates_page'), 'data-qa="rates-panel"'),
            ('modal', reverse('leads:request_modal'), 'data-booking'),
            ('calc', reverse('leads:calc_modal'), 'data-qa="calc"'),
        )
        for enabled in (False, True):
            self._mode(enabled)
            prefix = 'eo' if enabled else 'off'
            for label, url, marker in pages:
                html = self._html(url)
                self.assertIn(marker, html, label)
                self._assert_clean(html, '%s:%s' % (prefix, label))

    def test_static_js_does_not_start_removed_rate_timers(self):
        root = Path(settings.BASE_DIR) / 'src/core/static/js'
        files = [
            path for path in root.rglob('*.js')
            if path.name != 'htmx.min.js'
        ]
        self.assertGreater(len(files), 0)
        for path in files:
            text = path.read_text(encoding='utf-8')
            for needle in _JS_STARTS:
                self.assertNotIn(
                    needle,
                    text,
                    '%s: %s' % (path.name, needle),
                )
