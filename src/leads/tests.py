from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from src.bot.html import sanitize_bot_html
from src.core.templatetags.content_format import format_rate
from src.leads.models import ExchangeRequest
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard
from src.rates.selectors import get_quote, get_quotes_for_city


class FormatRateTests(TestCase):
    def test_compact_small_rate_keeps_four_decimals(self):
        self.assertEqual(format_rate(Decimal('0.11'), 'compact'), '0.1100')
        self.assertNotEqual(format_rate(Decimal('0.11'), 'compact'), '0,00')

    def test_ua_shows_two_decimals_and_comma(self):
        self.assertEqual(format_rate(Decimal('41.2000'), 'ua'), '41,20')
        self.assertEqual(format_rate(Decimal('41.2'), 'ua'), '41,20')
        self.assertEqual(format_rate('41.205', 'ua'), '41,21')
        self.assertEqual(format_rate(Decimal('2606151'), 'ua'), '2 606 151,00')
        self.assertEqual(format_rate(Decimal('-1.5'), 'ua'), '-1,50')
        self.assertEqual(format_rate(Decimal('0.11'), 'ua'), '0,11')
        self.assertEqual(format_rate('', 'ua'), '')
        self.assertEqual(format_rate('ні', 'ua'), 'ні')


class QuoteSelectorTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Київ', slug='kyiv', phone='+380992222222')
        self.ok = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-uah')
        self.bad = CurrencyPair.objects.create(code='HUF', name='Форинт', slug='huf-uah')
        Quote.objects.create(
            pair=self.ok,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('41.20'),
            sell=Decimal('41.60'),
        )
        Quote.objects.create(
            pair=self.bad,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('0'),
            sell=Decimal('0'),
        )

    def test_skips_zero_quotes(self):
        rows, _ = get_quotes_for_city(self.city, RateBoard.RETAIL)
        codes = {row['pair'].code for row in rows}
        self.assertIn('USD', codes)
        self.assertNotIn('HUF', codes)
        self.assertIsNone(get_quote(self.bad, self.city, RateBoard.RETAIL))


class ExchangeRequestHardeningTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(
            name='Харків', slug='kharkiv', phone='+380991111111', sort_order=0,
        )
        self.branch = Branch.objects.create(
            city=self.city, address='Харків, вул. 1', phone=self.city.phone,
        )
        self.pair = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-uah')
        Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('41.20'),
            sell=Decimal('41.60'),
        )
        self.client.post(reverse('network:set_city'), {'city': 'kharkiv'})

    def _payload(self, **overrides):
        data = {
            'name': 'Олег',
            'phone': '+380991234567',
            'pair': self.pair.pk,
            'board': RateBoard.RETAIL,
            'direction': 'sell',
            'amount_give': '100',
            'amount_receive': '1',
            'rate_fixed': '1',
            'branch': self.branch.pk,
            'consent': True,
        }
        data.update(overrides)
        return data

    def test_server_overwrites_client_rate(self):
        resp = self.client.post(reverse('leads:request_modal'), self._payload())
        self.assertEqual(resp.status_code, 200)
        obj = ExchangeRequest.objects.get()
        self.assertEqual(obj.rate_fixed, Decimal('41.2000'))
        self.assertEqual(obj.amount_receive, Decimal('4120.00'))

    @patch('src.leads.services.notify_new_lead')
    def test_duplicate_request_is_idempotent(self, notify):
        url = reverse('leads:request_modal')
        first = self.client.post(url, self._payload())
        second = self.client.post(url, self._payload())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ExchangeRequest.objects.count(), 1)
        self.assertEqual(notify.call_count, 1)

    def test_set_city_rejects_external_referer(self):
        resp = self.client.post(
            reverse('network:set_city'),
            {'city': 'kharkiv'},
            HTTP_REFERER='https://evil.example/phish',
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/')


class BotHtmlSanitizeTests(TestCase):
    def test_strips_script_keeps_bold(self):
        html = sanitize_bot_html('<b>Ок</b><script>alert(1)</script>')
        self.assertIn('<b>Ок</b>', html)
        self.assertNotIn('<script>', html)
        self.assertIn('alert(1)', html)
