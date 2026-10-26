import os
import re
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import Service
from src.core.models import SiteSettings
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_REVIEW_PAGES = frozenset({'home', 'services', 'faq'})
_LEAD_MARKERS = (
    'data-qa="contact-form"',
    'data-qa="modal-request"',
    'data-booking',
    'name="amount_give"',
)
_CALC_FIELDS = (
    'data-qa="home-calc"',
    'data-calc-amount',
    'data-calc-result',
    'data-calc-rate-label',
    'data-calc-from-code',
    'data-calc-to-code',
    'data-calc-swap',
)
_PAGE_BUTTONS = {
    'home': (
        'hero__fix-btn',
        'data-calc-continue',
        'data-qa="rate-request"',
        'data-qa="cta-request"',
    ),
    'rates': (
        'data-qa="rate-request"',
        'data-qa="cta-request"',
    ),
    'services': (
        'svc-row__cta',
        'data-qa="cta-request"',
    ),
    'pair': (
        'data-qa="cta-request"',
    ),
    'city': (
        'btn--ghost',
        'data-qa="cta-request"',
    ),
    'faq': (
        'data-qa="cta-request"',
    ),
    'contacts': (
        'data-qa="cta-request"',
    ),
}


class ContactButtonsTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._set_mode(False)
        self.contact = reverse('leads:contact_modal')
        self.request_modal = reverse('leads:request_modal')
        self.contact_submit = reverse('leads:contact_submit')
        self.review = reverse('reviews:review_submit')
        self.city = City.objects.create(
            name='Львів',
            slug='lviv',
            phone='+380321112233',
            sort_order=0,
            banner_button_mode='Зафіксувати курс',
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
            buy=Decimal('41.20'),
            sell=Decimal('41.80'),
        )
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut',
            short_desc='Готівковий обмін у касі',
            exchange_safe=True,
            block_cta='Зафіксувати курс',
            block_cta_mode='Зафіксувати курс',
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

    def _pages(self):
        return (
            ('home', reverse('core:home')),
            ('rates', reverse('rates:rates_page')),
            ('services', reverse('content:services')),
            ('pair', reverse('rates:pair_detail', kwargs={'slug': self.pair.slug})),
            ('city', reverse('network:city_detail', kwargs={'slug': self.city.slug})),
            ('faq', reverse('content:faq')),
            ('contacts', reverse('content:contacts')),
        )

    def _html(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def _button_tags(self, html):
        return re.findall(r'<button\b[^>]*>', html, flags=re.I)

    def _open_urls(self, html):
        return re.findall(r'data-open-modal="([^"]*)"', html)

    def _assert_no_lead(self, html, label):
        self.assertNotIn(self.request_modal, html, label)
        self.assertNotIn(self.contact_submit, html, label)
        for marker in _LEAD_MARKERS:
            self.assertNotIn(marker, html, '%s: %s' % (label, marker))
        for form in re.findall(r'<form\b[^>]*>', html, flags=re.I):
            self.assertNotIn(self.request_modal, form, label)
            self.assertNotIn(self.contact_submit, form, label)
            self.assertNotIn('contact-form', form, label)

    def _assert_openers(self, html, name, label):
        urls = self._open_urls(html)
        self.assertTrue(urls, label)
        allowed = {self.contact, self.review} if name in _REVIEW_PAGES else {self.contact}
        for url in urls:
            base = url.split('?', 1)[0]
            self.assertIn(base, allowed, '%s: %s' % (label, url))
        self.assertIn(self.contact, urls, label)

    def _assert_marked(self, html, marker, label):
        matched = [tag for tag in self._button_tags(html) if marker in tag]
        self.assertTrue(matched, '%s: немає %s' % (label, marker))
        needle = 'data-open-modal="%s"' % self.contact
        for tag in matched:
            self.assertIn(needle, tag, '%s: %s' % (label, marker))

    def test_pages_open_contact_modal_without_lead_form(self):
        for enabled in (False, True):
            self._set_mode(enabled)
            prefix = 'eo' if enabled else 'off'
            for name, url in self._pages():
                html = self._html(url)
                label = '%s:%s' % (prefix, name)
                self._assert_no_lead(html, label)
                self._assert_openers(html, name, label)
                for marker in _PAGE_BUTTONS[name]:
                    self._assert_marked(html, marker, label)
                mobile = [
                    tag for tag in self._button_tags(html)
                    if 'data-menu-close' in tag and 'data-open-modal' in tag
                ]
                self.assertTrue(mobile, label)
                self.assertIn(
                    'data-open-modal="%s"' % self.contact,
                    mobile[0],
                    label,
                )
            home = self._html(reverse('core:home'))
            for marker in _CALC_FIELDS:
                self.assertIn(marker, home, '%s:%s' % (prefix, marker))
            pair = self._html(
                reverse('rates:pair_detail', kwargs={'slug': self.pair.slug}),
            )
            self.assertRegex(
                pair,
                r'<button\b[^>]*data-open-modal="%s"[^>]*>\s*Створити заявку'
                % re.escape(self.contact),
            )
            calc = self._html(reverse('leads:calc_modal'))
            self.assertIn('contact-card', calc)
            self.assertIn('data-qa="modal-contact"', calc)
            self.assertNotIn('data-qa="calc"', calc)
            self.assertNotIn('data-calc-amount', calc)
            self.assertNotIn(self.request_modal, calc)
            self.assertNotIn('<form', calc.lower())
            self.assertNotIn('<input', calc.lower())

    def test_calc_script_keeps_math_and_does_not_open_request(self):
        script = (
            settings.BASE_DIR / 'src/core/static/js/calc.js'
        ).read_text(encoding='utf-8')
        booking = (
            settings.BASE_DIR / 'src/core/static/js/booking-modal.js'
        ).read_text(encoding='utf-8')
        base = (settings.BASE_DIR / 'templates/base.html').read_text(encoding='utf-8')
        self.assertNotIn('/htmx/zayavka/', script)
        self.assertNotIn('openModal', script)
        self.assertIn('function recalc(scope)', script)
        self.assertIn('function recalcCross()', script)
        self.assertIn('[data-calc-amount]', script)
        self.assertNotIn('/htmx/zayavka/', booking)
        self.assertNotIn('openModal', booking)
        self.assertIn("{% static 'js/calc.js' %}?v=18", base)
        self.assertTrue(reverse('leads:request_modal'))
