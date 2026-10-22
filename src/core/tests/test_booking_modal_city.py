import os
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.core.models import SiteSettings
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class BookingModalCityTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)
        self.kyiv = City.objects.create(
            name='Київ',
            slug='kyiv',
            phone='+380441111111',
            sort_order=0,
        )
        self.kharkiv = City.objects.create(
            name='Харків',
            slug='kharkiv',
            phone='+380442222222',
            sort_order=1,
        )
        Branch.objects.create(
            city=self.kyiv,
            address='Київ, вул. 1',
            phone=self.kyiv.phone,
        )
        Branch.objects.create(
            city=self.kharkiv,
            address='Харків, вул. 2',
            phone=self.kharkiv.phone,
        )
        self.usd = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
            exchange_safe=True,
        )
        self.btc = CurrencyPair.objects.create(
            code='BTC',
            name='Bitcoin',
            slug='btc-uah',
            exchange_safe=False,
        )
        self._quote(self.usd, self.kyiv, '41.20', '41.70')
        self._quote(self.usd, self.kharkiv, '41.25', '41.80')
        self._quote(self.btc, self.kyiv, '100', '110')
        self._quote(self.btc, self.kharkiv, '101', '111')

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

    def _quote(self, pair, city, buy, sell):
        Quote.objects.create(
            pair=pair,
            board=RateBoard.RETAIL,
            city=city,
            buy=Decimal(buy),
            sell=Decimal(sell),
        )

    def _buy(self, response, code):
        for item in response.json()['quotes']:
            if item['code'] == code:
                return Decimal(item['buy'])
        self.fail(code)

    def _quotes(self, **params):
        response = self.client.get(reverse('core:quotes_json'), params)
        self.assertEqual(response.status_code, 200)
        return response

    def test_quotes_json_city_returns_that_city_rate(self):
        kyiv = self._quotes(city='kyiv')
        kharkiv = self._quotes(city='kharkiv')
        self.assertEqual(self._buy(kyiv, 'USD'), Decimal('41.20'))
        self.assertEqual(self._buy(kharkiv, 'USD'), Decimal('41.25'))

        switched = self.client.post(reverse('network:set_city'), {'city': 'kharkiv'})
        self.assertEqual(switched.status_code, 302)
        bare = self._quotes(board='retail')
        self.assertEqual(self._buy(bare, 'USD'), Decimal('41.25'))
        override = self._quotes(city='kyiv', board='retail')
        self.assertEqual(self._buy(override, 'USD'), Decimal('41.20'))

    def test_modal_city_select_exposes_quote_data(self):
        response = self.client.get(reverse('leads:request_modal'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        quotes_url = reverse('core:quotes_json')
        self.assertIn('data-bk-city', html)
        self.assertIn('data-quotes-url="%s"' % quotes_url, html)
        self.assertIn('data-city="kyiv"', html)
        self.assertIn('data-city="kharkiv"', html)
        script = (
            settings.BASE_DIR / 'src/core/static/js/booking-modal.js'
        ).read_text(encoding='utf-8')
        base = (settings.BASE_DIR / 'templates/base.html').read_text(encoding='utf-8')
        self.assertIn("getAttribute('data-city')", script)
        self.assertIn("getAttribute('data-quotes-url')", script)
        self.assertIn("'board=retail&city=' + encodeURIComponent(slug)", script)
        self.assertIn('loadCityQuotes()', script)
        self.assertIn("{% static 'js/booking-modal.js' %}?v=4", base)

    def test_exchange_only_keeps_visible_pairs(self):
        self._mode(True)
        hidden = self._quotes(city='kyiv')
        codes = [item['code'] for item in hidden.json()['quotes']]
        self.assertIn('USD', codes)
        self.assertNotIn('BTC', codes)
        modal = self.client.get(reverse('leads:request_modal'))
        shown = [item['code'] for item in modal.context['currencies']]
        self.assertIn('USD', shown)
        self.assertNotIn('BTC', shown)

        self._mode(False)
        opened = [item['code'] for item in self._quotes(city='kharkiv').json()['quotes']]
        self.assertIn('USD', opened)
        self.assertIn('BTC', opened)
