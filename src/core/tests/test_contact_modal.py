import os
import re

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.core.exchange_stopwords import STOP_WORDS
from src.core.models import SiteSettings
from src.core.phones import phone_tel
from src.network.models import Branch, City

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_EXTRA_STOPS = ('замін',)
_SHORT = frozenset({
    'eth', 'btc', 'bnb', 'sol', 'trx', 'ton', 'gold', 'swift', 'usdt', 'usdc',
})
_PHONE = '+38 (067) 111-22-33'


def _stop_hits(html):
    """Ті самі межі слова, що в павуку режиму: короткі токени не чіпають «button»."""
    lowered = html.casefold()
    hits = []
    for word in (*STOP_WORDS, *_EXTRA_STOPS):
        token = word.casefold()
        parts = token.split()
        if len(parts) > 1:
            pattern = r'\s+'.join(
                rf'(?<!\w){re.escape(part)}(?!\w)' if len(part) < 4 or part in _SHORT
                else rf'(?<!\w){re.escape(part)}'
                for part in parts
            )
        elif len(token) < 4 or token in _SHORT:
            pattern = rf'(?<!\w){re.escape(token)}(?!\w)'
        else:
            pattern = rf'(?<!\w){re.escape(token)}'
        if re.search(pattern, lowered):
            hits.append(token)
    return hits
_CITY_PHONE = '+38 (044) 200-30-40'
_BRANCH_PHONE = '+38 (032) 300-40-50'
_TELEGRAM = 'https://t.me/s/Obmin_Desk?start=1'
_NICK = '@Obmin_Desk'


class ContactModalTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._set_mode(False)

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

    def _settings(self, phone, telegram):
        site = SiteSettings.load()
        site.default_phone = phone
        site.telegram_url = telegram
        site.save()
        cache.clear()

    def _city(self, slug, phone):
        return City.objects.create(name='Львів', slug=slug, phone=phone, sort_order=0)

    def _branch(self, city, phone):
        return Branch.objects.create(
            city=city,
            address='вул. Липова, 4',
            phone=phone,
        )

    def _html(self):
        response = self.client.get(reverse('leads:contact_modal'))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_modal_shows_settings_phone_and_telegram_nick(self):
        self._settings(_PHONE, _TELEGRAM)
        city = self._city('lviv-contact', '')
        self._branch(city, '')
        html = self._html()
        self.assertIn(f'href="tel:{phone_tel(_PHONE)}"', html)
        self.assertIn(_PHONE, html)
        self.assertIn(f'href="{_TELEGRAM}"', html)
        self.assertIn(_NICK, html)
        self.assertNotIn('@s<', html)
        self.assertNotIn('<form', html.lower())
        self.assertNotIn('<input', html.lower())
        self.assertIn('Зателефонувати', html)
        self.assertIn('Написати в Telegram', html)
        self.assertLess(
            html.index('contact-card--phone'),
            html.index('contact-card--telegram'),
        )
        base = (settings.BASE_DIR / 'templates/base.html').read_text(encoding='utf-8')
        self.assertIn("{% static 'css/components/contact-modal.css' %}?v=1", base)

    def test_branch_phone_before_city_and_default(self):
        self._settings(_PHONE, _TELEGRAM)
        city = self._city('lviv-branch-phone', _CITY_PHONE)
        self._branch(city, _BRANCH_PHONE)
        html = self._html()
        self.assertIn(f'href="tel:{phone_tel(_BRANCH_PHONE)}"', html)
        self.assertIn(_BRANCH_PHONE, html)
        self.assertNotIn(f'href="tel:{phone_tel(_CITY_PHONE)}"', html)
        self.assertNotIn(f'href="tel:{phone_tel(_PHONE)}"', html)

    def test_city_phone_when_branch_empty(self):
        self._settings(_PHONE, _TELEGRAM)
        city = self._city('lviv-city-phone', _CITY_PHONE)
        self._branch(city, '')
        html = self._html()
        self.assertIn(f'href="tel:{phone_tel(_CITY_PHONE)}"', html)
        self.assertIn(_CITY_PHONE, html)
        self.assertNotIn(f'href="tel:{phone_tel(_PHONE)}"', html)

    def test_empty_phone_omits_tel(self):
        self._settings('', _TELEGRAM)
        city = self._city('lviv-no-phone', '')
        self._branch(city, '   ')
        html = self._html()
        self.assertNotIn('tel:', html)
        self.assertNotIn('contact-card--phone', html)
        self.assertIn(_TELEGRAM, html)
        self.assertIn(_NICK, html)

    def test_empty_telegram_omits_tme(self):
        self._settings(_PHONE, '')
        html = self._html()
        self.assertNotIn('t.me', html.lower())
        self.assertNotIn('contact-card--telegram', html)
        self.assertIn(f'href="tel:{phone_tel(_PHONE)}"', html)

    def test_exchange_mode_has_no_stop_words(self):
        self._settings(_PHONE, 'https://t.me/obmin_desk')
        self._set_mode(True)
        response = self.client.get(reverse('leads:contact_modal'))
        self.assertEqual(response.status_code, 200)
        hits = _stop_hits(response.content.decode())
        self.assertEqual(hits, [])

    def test_home_still_opens_request_modal(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(reverse('leads:request_modal'), html)
        self.assertNotIn(reverse('leads:contact_modal'), html)
