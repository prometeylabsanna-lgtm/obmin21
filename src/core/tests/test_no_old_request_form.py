import os

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.core.models import SiteSettings
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_OLD_FORM = (
    'name="phone"',
    'Надіслати заявку',
    'Крок 2',
    '30:00',
    '<form',
    '<input',
)
_PAGE_COPY = (
    'name="phone"',
    'Надіслати заявку',
    'Крок 2',
    '30:00',
    'data-qa="modal-request"',
    'data-qa="booking-form"',
    'Попередній розрахунок',
)


class NoOldRequestFormTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._set_mode(False)
        self.city = City.objects.create(
            name='Львів',
            slug='lviv',
            phone='+380321112233',
            sort_order=0,
        )
        Branch.objects.create(
            city=self.city,
            address='вул. Липова, 4',
            phone=self.city.phone,
        )
        self.pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
            exchange_safe=True,
        )
        Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=self.city,
            buy='41.20',
            sell='41.80',
        )

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _set_mode(self, enabled):
        site = SiteSettings.load()
        site.exchange_only = enabled
        site.save()
        cache.clear()

    def _html(self, url, **params):
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def _modal_urls(self):
        pair = str(self.pair.pk)
        query = (
            {},
            {'pair': pair, 'amount': '1000'},
            {'pair': pair, 'amount': '2500', 'amount_give': '2500'},
        )
        urls = (
            reverse('leads:request_modal'),
            reverse('leads:calc_modal'),
        )
        for url in urls:
            for params in query:
                yield url, params

    def test_get_modals_return_contact_window(self):
        for enabled in (False, True):
            self._set_mode(enabled)
            contact = self._html(reverse('leads:contact_modal'))
            self.assertIn('contact-card', contact)
            prefix = 'eo' if enabled else 'off'
            for url, params in self._modal_urls():
                html = self._html(url, **params)
                label = '%s %s %s' % (prefix, url, params)
                self.assertEqual(html, contact, label)
                self.assertIn('contact-card', html, label)
                lowered = html.lower()
                for needle in _OLD_FORM:
                    haystack = lowered if needle.startswith('<') else html
                    self.assertNotIn(needle, haystack, '%s: %s' % (label, needle))

    def test_public_pages_omit_old_request_form(self):
        pages = (
            reverse('core:home'),
            reverse('rates:rates_page'),
            reverse('content:services'),
            reverse('content:advantages'),
            reverse('content:faq'),
            reverse('content:contacts'),
            reverse('network:city_detail', kwargs={'slug': self.city.slug}),
            reverse('rates:pair_detail', kwargs={'slug': self.pair.slug}),
        )
        for enabled in (False, True):
            self._set_mode(enabled)
            prefix = 'eo' if enabled else 'off'
            for url in pages:
                html = self._html(url)
                for needle in _PAGE_COPY:
                    self.assertNotIn(needle, html, '%s %s: %s' % (prefix, url, needle))
