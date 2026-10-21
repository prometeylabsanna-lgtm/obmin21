import os

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import Service
from src.core.models import SiteSettings

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')

_FORBIDDEN = (
    'bitcoin.png',
    'КРИПТОВАЛЮТА',
    'ЗОЛОТО',
    'ПЕРЕКАЗИ',
    'ОПТОВИЙ',
    'ЗНОШЕНИХ',
)

_HEADER_NAV = (
    'data-qa="nav-services"',
    'data-qa="nav-advantages"',
    'data-qa="nav-faq"',
    'data-qa="nav-blog"',
    'data-qa="nav-contacts"',
)

_FOOTER_SERVICES = (
    ('Обмін валют', 'obmin-valiut', True, 1),
    ('Грошові перекази', 'hroshovi-perekazy', False, 2),
    ('Криптовалюта', 'kryptovaliuta', False, 3),
    ('Інвестиційне золото', 'investytsiine-zoloto', False, 4),
    ('Оптовий обмін', 'optovyi-obmin', False, 5),
    ('Заміна зношених купюр', 'zamina-znoshenykh', False, 6),
)


class ExchangeOnlyChromeTemplateTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        for title, slug, exchange_safe, sort_order in _FOOTER_SERVICES:
            Service.objects.create(
                title=title,
                slug=slug,
                short_desc='Послуга',
                exchange_safe=exchange_safe,
                sort_order=sort_order,
            )

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _set_mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)

    def _page(self):
        return self.client.get(reverse('content:privacy'))

    def _services_href(self, slug):
        return f'{reverse("content:services")}#svc-{slug}'

    def test_mode_off_renders_footer_services_and_bitcoin_icon(self):
        self._set_mode(False)
        response = self._page()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(html.count('bitcoin.png'), 5)
        for marker in _HEADER_NAV:
            self.assertContains(response, marker)
        for title, slug, _safe, _order in _FOOTER_SERVICES:
            self.assertContains(response, title.upper())
            self.assertContains(response, self._services_href(slug))
        self.assertNotContains(response, '#svc-1')
        self.assertNotContains(response, '#svc-6')
        self.assertContains(response, 'ВІДГУКИ')
        header = html[html.index('<header'):html.index('</header>')]
        for token in _FORBIDDEN:
            self.assertNotIn(token, header)

    def test_mode_off_without_services_has_no_hardcoded_footer_list(self):
        Service.objects.all().delete()
        self._set_mode(False)
        response = self._page()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(html.count('bitcoin.png'), 5)
        for token in ('КРИПТОВАЛЮТА', 'ЗОЛОТО', 'ПЕРЕКАЗИ', 'ОПТОВИЙ', 'ЗНОШЕНИХ'):
            self.assertNotContains(response, token)
        self.assertNotContains(response, '#svc-1')
        for marker in _HEADER_NAV:
            self.assertContains(response, marker)

    def test_mode_on_hides_forbidden_chrome(self):
        self._set_mode(True)
        response = self._page()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for token in _FORBIDDEN:
            self.assertNotIn(token, html)
        self.assertContains(response, 'ОБМІН ВАЛЮТ')
        self.assertContains(response, self._services_href('obmin-valiut'))
        self.assertNotContains(response, self._services_href('hroshovi-perekazy'))
        self.assertNotContains(response, self._services_href('investytsiine-zoloto'))
        self.assertNotContains(response, self._services_href('optovyi-obmin'))
        self.assertNotContains(response, self._services_href('zamina-znoshenykh'))
        for marker in _HEADER_NAV:
            self.assertContains(response, marker)
        self.assertContains(response, '>Послуги')
        self.assertContains(response, '>Контакти')
        self.assertContains(response, 'ВІДГУКИ')
        self.assertContains(response, 'ПОЛІТИКА КОНФІДЕНЦІЙНОСТІ')

    def test_mode_on_without_visible_services_has_no_fallback_links(self):
        self._set_mode(True)
        Service.objects.update(exchange_safe=False)
        response = self._page()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for token in _FORBIDDEN:
            self.assertNotIn(token, html)
        lowered = html.lower()
        for token in ('крипт', 'золот', 'переказ', 'оптов', 'зношен'):
            self.assertNotIn(token, lowered)
        footer = html[html.index('<footer'):html.index('</footer>')]
        self.assertNotIn('#svc-', footer)
        self.assertNotIn('display:none', ''.join(lowered.split()))
