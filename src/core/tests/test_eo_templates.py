import os

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import AdvantagesPage, FaqItem, HomePage, Service
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


_HOME_STOPS = (
    'крипт',
    'crypto',
    'usdt',
    'usdc',
    'btc',
    'bitcoin',
    'біткоїн',
    'eth',
    'swift',
    'переказ',
    'transfer',
    'золот',
    'gold',
    'оптов',
    'зношен',
    'електронн',
)

_PROMO_IMAGES = (
    'coins.png',
    'promo-transfers.png',
    'promo-swift.png',
)


class ExchangeOnlyHomeTemplateTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valiut',
            short_desc='Готівковий обмін у відділенні',
            exchange_safe=True,
            sort_order=1,
        )
        Service.objects.create(
            title='Грошові перекази',
            slug='hroshovi-perekazy',
            short_desc='Переказ готівки по Україні',
            exchange_safe=False,
            sort_order=2,
        )
        Service.objects.create(
            title='Інвестиційне золото',
            slug='investytsiine-zoloto',
            short_desc='Золоті зливки',
            exchange_safe=False,
            sort_order=3,
        )
        FaqItem.objects.create(
            question='Який курс долара у відділенні?',
            answer='Курс фіксується на тридцять хвилин.',
            exchange_safe=True,
            sort_order=1,
        )
        FaqItem.objects.create(
            question='Як надіслати переказ SWIFT?',
            answer='SWIFT іде на рахунок за кордоном.',
            exchange_safe=False,
            sort_order=2,
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
        cache.clear()

    def _home(self):
        return self.client.get(reverse('core:home'))

    def _between(self, html, start, end):
        begin = html.index(start)
        finish = html.index(end, begin + len(start))
        return html[begin:finish]

    def _sections(self, html):
        return {
            'slider': self._between(html, 'data-qa="promo-banner"', 'data-qa="section-map"'),
            'rates': self._between(html, 'id="rates-panel"', 'id="calculator"'),
            'services': self._between(html, 'data-qa="section-services"', 'data-qa="section-faq"'),
            'faq': self._between(html, 'data-qa="section-faq"', 'data-qa="section-reviews"'),
        }

    def _assert_no_stops(self, chunk, label):
        lowered = chunk.lower()
        for token in _HOME_STOPS:
            self.assertNotIn(token, lowered, label)

    def test_mode_off_keeps_slides_dots_and_crypto_tab(self):
        self._set_mode(False)
        response = self._home()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for name in _PROMO_IMAGES:
            self.assertIn(name, html)
        self.assertIn('bills.png', html)
        self.assertIn('USD та EUR', html)
        self.assertEqual(html.count('data-promo-dot '), 4)
        self.assertEqual(html.count('data-promo-slide'), 4)
        self.assertNotIn('data-autoplay="0"', html)
        self.assertNotIn('data-slides="1"', html)
        self.assertContains(response, 'data-qa="rates-tab-crypto"')
        self.assertContains(response, '>Крипто<')
        self.assertContains(response, 'Грошові перекази')
        self.assertContains(response, 'Інвестиційне золото')
        self.assertContains(response, 'Обмін валют')
        self.assertContains(response, 'Як надіслати переказ SWIFT?')
        self.assertContains(response, 'Який курс долара у відділенні?')
        self.assertContains(response, 'services-section__lead')
        self.assertContains(response, 'міжнародні перекази')
        self.assertContains(response, 'криптоактивів')
        self.assertContains(response, 'articles-section__lead')

    def test_mode_on_hides_forbidden_home_blocks(self):
        self._set_mode(True)
        response = self._home()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for name in _PROMO_IMAGES:
            self.assertNotIn(name, html)
        self.assertNotIn('data-promo-dot', html)
        self.assertNotIn('data-qa="rates-tab-crypto"', html)
        self.assertNotIn('>Крипто<', html)
        self.assertNotIn('Криптовалюта', html)
        self.assertIn('data-autoplay="0"', html)
        self.assertIn('data-slides="1"', html)
        self.assertEqual(html.count('data-promo-slide'), 1)
        self.assertIn('bills.png', html)
        self.assertIn('USD та EUR', html)
        self.assertIn('Обмін валют', html)
        self.assertIn('Який курс долара у відділенні?', html)
        self.assertNotIn('Грошові перекази', html)
        self.assertNotIn('Інвестиційне золото', html)
        self.assertNotIn('Як надіслати переказ SWIFT?', html)
        self.assertNotIn('services-section__lead', html)
        self.assertNotIn('articles-section__lead', html)
        self.assertNotIn('міжнародні перекази', html)
        self.assertNotIn('криптоактивів', html)
        self.assertNotIn('display:none', ''.join(html.lower().split()))
        for label, chunk in self._sections(html).items():
            self._assert_no_stops(chunk, label)

    def test_mode_on_articles_lead_mode_replaces_default(self):
        page = HomePage.load()
        page.articles_lead_mode = 'Курси готівки у відділеннях'
        page.save()
        self._set_mode(True)
        html = self._home().content.decode()
        self.assertIn('Курси готівки у відділеннях', html)
        self.assertIn('articles-section__lead', html)
        self.assertNotIn('міжнародні перекази', html)
        self.assertNotIn('електронних валют', html)
        self._set_mode(False)
        off = self._home().content.decode()
        self.assertIn('міжнародні перекази', off)
        self.assertNotIn('Курси готівки у відділеннях', off)

    def test_mode_on_omits_stats_fallback(self):
        stats = AdvantagesPage.load()
        for index in range(1, 5):
            setattr(stats, f'stat_{index}_title', '')
            setattr(stats, f'stat_{index}_text', '')
        stats.save()
        self._set_mode(False)
        off = self._home().content.decode()
        self.assertIn('Постійних клієнтів', off)
        self.assertIn('швидкого та зручного обміну валют', off)
        self._set_mode(True)
        on = self._home().content.decode()
        self.assertNotIn('Постійних клієнтів', on)
        self.assertNotIn('криптоактивів', on)
        self.assertNotIn('швидкого та зручного обміну валют', on)
