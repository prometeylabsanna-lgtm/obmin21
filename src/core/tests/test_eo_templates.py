import os
import re
from datetime import timedelta
from pathlib import Path

from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from src.blog.models import Category, Post
from src.content.models import (
    AdvantagesPage,
    BlogPage,
    CitiesPage,
    ContactsPage,
    FaqItem,
    FaqPage,
    HomePage,
    HomeStat,
    PrivacyPage,
    RatesPage,
    ReviewsPage,
    Service,
    ServicesPage,
)
from src.core.exchange_mode import NEUTRAL_DESCRIPTION
from src.core.models import SiteSettings
from src.network.models import Branch, City

def setUpModule():
    from django.core.management import call_command
    from django.db import connection

    if 'core_sitesettings' not in connection.introspection.table_names():
        call_command('migrate', verbosity=0, interactive=False)


def _blank_text_modes(page):
    for field in page._meta.fields:
        if not field.name.endswith('_mode'):
            continue
        if field.get_internal_type() not in ('CharField', 'TextField'):
            continue
        setattr(page, field.name, '')


class ExchangeTemplateCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
from src.rates.models import CurrencyPair

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


class ExchangeOnlyChromeTemplateTests(ExchangeTemplateCase):
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


class ExchangeOnlyHomeTemplateTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        home = HomePage.load()
        home.services_lead_mode = ''
        home.articles_lead_mode = ''
        home.save(update_fields=['services_lead_mode', 'articles_lead_mode'])
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


_WORD_STOPS = ('eth', 'btc', 'gold', 'swift', 'usdt', 'usdc')
_SERVICES_LEAD = (
    'Окрім обміну валют у мережі Обмін21 доступні грошові перекази по Україні, '
    'міжнародні перекази та обмін електронних валют — умови та підготовка до візиту нижче.'
)
_INTRO_MODE = 'Курси готівки у відділеннях мережі'
_BANNER_TITLE = 'Обмін валют і криптовалюта'
_BANNER_TEXT = 'Перекази, золото та оптовий курс'
_TITLE_MODE = 'Готівковий обмін'
_TEXT_MODE = 'Фіксуйте курс долара у відділенні'
_RAW_INTRO = 'Сирий вступ про криптовалюту'


def _assert_clean(test, html, label):
    lowered = html.lower()
    for token in _HOME_STOPS:
        if token in _WORD_STOPS:
            found = re.search(
                r'(?<![0-9a-zа-яіїєґ])' + re.escape(token) + r'(?![0-9a-zа-яіїєґ])',
                lowered,
            )
            test.assertIsNone(found, label)
        else:
            test.assertNotIn(token, lowered, label)


class ExchangeOnlyServicesCityTemplateTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = ServicesPage.load()
        page.intro = _RAW_INTRO
        page.intro_mode = _INTRO_MODE
        page.hero_text_mode = ''
        page.seo_description = 'Курси готівки у відділеннях.'
        page.save()
        home = HomePage.load()
        home.articles_lead_mode = ''
        home.services_lead_mode = ''
        home.save(update_fields=['articles_lead_mode', 'services_lead_mode'])
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valiut',
            short_desc='Готівковий обмін долара та євро у відділенні',
            exchange_safe=True,
            sort_order=1,
        )
        Service.objects.create(
            title='Грошові перекази',
            slug='groshovi-perekazy',
            short_desc='Переказ готівки',
            exchange_safe=False,
            sort_order=2,
        )
        Service.objects.create(
            title='Інвестиційне золото',
            slug='investytsiine-zoloto',
            short_desc='Зливки',
            exchange_safe=False,
            sort_order=3,
        )
        Service.objects.create(
            title='Оптовий обмін',
            slug='optovyi-obmin',
            short_desc='Курс для великої суми',
            exchange_safe=False,
            sort_order=4,
        )
        Service.objects.create(
            title='Заміна зношених купюр',
            slug='zamina-znoshenykh-kupiur',
            short_desc='Старі банкноти',
            exchange_safe=False,
            sort_order=5,
        )
        Service.objects.create(
            title='Криптовалюта',
            slug='krypto-kartka',
            short_desc='Картка партнера',
            exchange_safe=False,
            sort_order=6,
        )
        FaqItem.objects.create(
            question='Який курс долара у відділенні?',
            answer='Курс фіксується на тридцять хвилин.',
            exchange_safe=True,
            sort_order=1,
        )
        FaqItem.objects.create(
            question='Як надіслати переказ золота?',
            answer='SWIFT для зливків.',
            exchange_safe=False,
            sort_order=2,
        )
        category = Category.objects.create(name='Курси', slug='kursy')
        Post.objects.create(
            category=category,
            title='Курс долара у касі',
            title_mode='Курс долара у касі',
            slug='kurs-u-kasi',
            excerpt='Як зафіксувати курс долара.',
            body='Фіксація курсу на тридцять хвилин.',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        Post.objects.create(
            category=category,
            title='Міжнародні перекази і золото',
            slug='mizhnarodni-perekazy',
            excerpt='Умови переказу та зливків.',
            body='Текст про переказ.',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        self.city = City.objects.create(
            name='Львів',
            slug='lviv',
            phone='+380671112233',
            banner_title=_BANNER_TITLE,
            banner_text=_BANNER_TEXT,
            banner_title_mode=_TITLE_MODE,
            banner_text_mode=_TEXT_MODE,
            sort_order=0,
        )
        Branch.objects.create(
            city=self.city,
            address='пл. Ринок, 12, Львів',
            hours='Пн–Нд, 09:00–18:00',
            phone='+380671112233',
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

    def _services(self):
        return self.client.get(reverse('content:services'))

    def _city(self):
        return self.client.get(reverse('network:city_detail', kwargs={'slug': 'lviv'}))

    def _hero(self, html):
        start = html.index('class="hero"')
        finish = html.index('class="calc-head"', start)
        return html[start:finish]

    def test_mode_off_keeps_services_page_and_city_banner(self):
        self._set_mode(False)
        services = self._services()
        self.assertEqual(services.status_code, 200)
        html = services.content.decode()
        main = html[html.index('<main'):html.index('</main>')]
        self.assertIn(_RAW_INTRO, main)
        self.assertIn('articles-section__lead', main)
        self.assertNotIn(_SERVICES_LEAD, html)
        self.assertIn('переказ', html.lower())
        self.assertIn('swift', html.lower())
        self.assertIn('криптовалюти', main)
        self.assertIn('інвестиційне золото', main)
        self.assertIn('Грошові перекази', main)
        self.assertIn('Міжнародні перекази у 100+ країн', main)
        self.assertIn('Оптовий обмін', main)
        self.assertIn('Заміна зношених купюр', main)
        self.assertIn('Криптовалюта', main)
        self.assertIn('Обмін валют', main)
        self.assertIn('Як надіслати переказ золота?', main)
        self.assertIn('Який курс долара у відділенні?', main)
        self.assertIn('Міжнародні перекази і золото', main)
        self.assertIn('Курс долара у касі', main)
        self.assertNotIn(_INTRO_MODE, html)
        self.assertEqual(html.count('bitcoin.png'), 5)
        city = self._city()
        self.assertEqual(city.status_code, 200)
        city_html = city.content.decode()
        self.assertIn('Львів', city_html)
        self.assertIn('пл. Ринок, 12, Львів', city_html)
        self.assertIn('Пн–Нд, 09:00–18:00', city_html)
        self.assertIn('Обрати це місто', city_html)
        self.assertNotIn(_TITLE_MODE, city_html)
        self.assertNotIn(_TEXT_MODE, city_html)
        self.assertNotIn(_BANNER_TITLE, city_html)
        self.assertNotIn('page-hero__lead', city_html)
        home = self.client.get(reverse('core:home')).content.decode()
        hero = self._hero(home)
        self.assertIn(_BANNER_TITLE, hero)
        self.assertIn(_BANNER_TEXT, hero)
        self.assertNotIn(_TITLE_MODE, hero)
        self.assertNotIn(_TEXT_MODE, hero)
        self.assertIn('переказ', home.lower())
        self.assertIn('swift', home.lower())

    def test_mode_on_services_and_city_use_mode_texts(self):
        self._set_mode(True)
        services = self._services()
        self.assertEqual(services.status_code, 200)
        html = services.content.decode()
        main = html[html.index('<main'):html.index('</main>')]
        self.assertIn(_INTRO_MODE, main)
        self.assertIn('articles-section__lead', main)
        self.assertIn('Обмін валют', main)
        self.assertNotIn('Готівковий обмін долара та євро у відділенні', main)
        self.assertIn('Який курс долара у відділенні?', main)
        self.assertIn('Курс долара у касі', main)
        self.assertNotIn(_SERVICES_LEAD, html)
        self.assertNotIn(_RAW_INTRO, html)
        self.assertNotIn('криптовалюти', html)
        self.assertNotIn('Грошові перекази', html)
        self.assertNotIn('Міжнародні перекази', html)
        self.assertNotIn('Інвестиційне золото', html)
        self.assertNotIn('Оптовий обмін', html)
        self.assertNotIn('зношених', html)
        self.assertNotIn('Як надіслати переказ золота?', html)
        self.assertNotIn('Міжнародні перекази і золото', html)
        self.assertNotIn('bitcoin.png', html)
        self.assertNotIn('svc-hero__lead', main)
        self.assertNotIn('display:none', ''.join(html.lower().split()))
        _assert_clean(self, html, 'posluhy')
        city = self._city()
        self.assertEqual(city.status_code, 200)
        city_html = city.content.decode()
        self.assertIn(_TITLE_MODE, city_html)
        self.assertIn(_TEXT_MODE, city_html)
        self.assertIn('пл. Ринок, 12, Львів', city_html)
        self.assertIn('Обрати це місто', city_html)
        self.assertNotIn(_BANNER_TITLE, city_html)
        self.assertNotIn(_BANNER_TEXT, city_html)
        self.assertNotIn('bitcoin.png', city_html)
        self.assertNotIn('display:none', ''.join(city_html.lower().split()))
        _assert_clean(self, city_html, 'city')
        home = self.client.get(reverse('core:home')).content.decode()
        hero = self._hero(home)
        self.assertIn(_TITLE_MODE, hero)
        self.assertIn(_TEXT_MODE, hero)
        self.assertNotIn(_BANNER_TITLE, hero)
        self.assertNotIn(_BANNER_TEXT, hero)
        self.assertNotIn('криптовалюта', hero.lower())
        _assert_clean(self, hero, 'hero')

    def test_mode_on_empty_mode_fields_omit_blocks(self):
        page = ServicesPage.load()
        page.intro_mode = ''
        page.save()
        self.city.banner_title_mode = ''
        self.city.banner_text_mode = ''
        self.city.save()
        self._set_mode(True)
        html = self._services().content.decode()
        main = html[html.index('<main'):html.index('</main>')]
        self.assertNotIn('articles-section__lead', main)
        self.assertNotIn(_SERVICES_LEAD, html)
        self.assertNotIn('svc-hero__lead', main)
        self.assertNotIn('криптовалюти', html)
        _assert_clean(self, html, 'posluhy-empty')
        city_html = self._city().content.decode()
        self.assertNotIn('page-hero__lead', city_html)
        self.assertNotIn(_BANNER_TITLE, city_html)
        self.assertIn('пл. Ринок, 12, Львів', city_html)
        _assert_clean(self, city_html, 'city-empty')
        hero = self._hero(self.client.get(reverse('core:home')).content.decode())
        self.assertNotIn('data-hero-title', hero)
        self.assertNotIn('data-hero-lead', hero)
        self.assertNotIn(_BANNER_TITLE, hero)
        self.assertNotIn(_BANNER_TEXT, hero)
        self.assertIn('у Львові', hero)
        _assert_clean(self, hero, 'hero-empty')

    def test_mode_on_empty_block_text_mode_omits_regular_text(self):
        self._set_mode(True)
        html = self._services().content.decode()
        self.assertIn('id="svc-obmin-valiut"', html)
        self.assertNotIn('Готівковий обмін долара та євро у відділенні', html)
        self.assertNotIn('svc-row__text', html)

    def test_mode_off_empty_intro_shows_original_lead(self):
        page = ServicesPage.load()
        page.intro = ''
        page.intro_mode = ''
        page.save()
        self._set_mode(False)
        html = self._services().content.decode()
        self.assertIn(_SERVICES_LEAD, html)
        self.assertIn('articles-section__lead', html)
        self.assertIn('<p class="svc-row__text">', html)
        self.assertIn('svc-row__cta', html)
        self.assertIn('svc-hero__lead', html)

    def test_mode_on_home_and_services_drop_transfer_words(self):
        self._set_mode(True)
        home = self.client.get(reverse('core:home')).content.decode()
        services = self._services().content.decode()
        for label, html in (('home', home), ('posluhy', services)):
            lowered = html.lower()
            self.assertNotIn('переказ', lowered, label)
            self.assertNotIn('swift', lowered, label)
            self.assertNotIn(_SERVICES_LEAD, html, label)
            self.assertNotIn('постійних клієнтів', lowered, label)
            self.assertNotIn('криптоактивів', lowered, label)
            self.assertNotIn('швидкого та зручного обміну валют', lowered, label)
            self.assertNotIn('display:none', ''.join(lowered.split()), label)
        self.assertIn(_TITLE_MODE, home)
        self.assertIn(_TEXT_MODE, home)
        self.assertNotIn(_BANNER_TITLE, home)
        self.assertNotIn(_BANNER_TEXT, home)
        self.assertIn(_INTRO_MODE, services)
        self.assertNotIn(_RAW_INTRO, services)
        self.assertNotIn('svc-hero__lead', services)


_SEO_HIDDEN_SERVICES = (
    ('Грошові перекази', 'groshovi-perekazy', 'Переказ SWIFT за кордон'),
    ('Криптовалюта', 'kryptovalyuta', 'Картка партнера'),
    ('Інвестиційне золото', 'investytsiine-zoloto', 'Зливки'),
    ('Оптовий обмін', 'optovyi-obmin', 'Курс для великої суми'),
    ('Заміна зношених купюр', 'zamina-znoshenykh-kupiur', 'Старі банкноти'),
)
_SAFE_POST_SLUG = 'kurs-u-kasi'
_SAFE_POST_TITLE = 'Курс долара у касі'
_HIDDEN_POST_SLUG = 'perekaz-swift'
_HIDDEN_POST_TITLE = 'Міжнародні перекази SWIFT'
_HERO_TRANSFER = 'перекази та інвестиційне золото'
_BLOCK_TRANSFER = 'Міжнародні перекази у 100+ країн'


def _assert_no_transfer_words(test, html, label):
    lowered = html.lower()
    test.assertNotIn('переказ', lowered, label)
    found = re.search(
        r'(?<![0-9a-zа-яіїєґ])swift(?![0-9a-zа-яіїєґ])',
        lowered,
    )
    test.assertIsNone(found, label)


class ExchangeOnlySeoLinksTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = ServicesPage.load()
        page.seo_title = 'Послуги обміну валют'
        page.seo_description = 'Готівковий обмін долара та євро у відділеннях.'
        page.hero_text_mode = ''
        page.save()
        home = HomePage.load()
        home.articles_lead_mode = ''
        home.services_lead_mode = ''
        home.save(update_fields=['articles_lead_mode', 'services_lead_mode'])
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut',
            short_desc='Готівковий обмін долара та євро у відділенні',
            exchange_safe=True,
            show_on_home=True,
            sort_order=1,
        )
        for index, (title, slug, short_desc) in enumerate(_SEO_HIDDEN_SERVICES, start=2):
            Service.objects.create(
                title=title,
                slug=slug,
                short_desc=short_desc,
                exchange_safe=False,
                show_on_home=True,
                sort_order=index,
            )
        rates = Category.objects.create(name='Курси', slug='kursy-gotivky', sort_order=1)
        transfers = Category.objects.create(name='Перекази', slug='perekazy', sort_order=2)
        now = timezone.now()
        self.safe_post = Post.objects.create(
            category=rates,
            title=_SAFE_POST_TITLE,
            title_mode=_SAFE_POST_TITLE,
            slug=_SAFE_POST_SLUG,
            excerpt='Як зафіксувати курс долара.',
            body='Фіксація курсу на тридцять хвилин.',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
            published_at=now - timedelta(days=1),
        )
        hidden = Post.objects.create(
            category=transfers,
            title=_HIDDEN_POST_TITLE,
            slug=_HIDDEN_POST_SLUG,
            excerpt='Умови переказу за кордон.',
            body='Текст про переказ SWIFT.',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
            published_at=now,
        )
        self.safe_post.related_posts.add(hidden)

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

    def _pages(self):
        pages = {
            'home': self.client.get(reverse('core:home')),
            'services': self.client.get(reverse('content:services')),
            'blog': self.client.get(reverse('blog:post_list')),
            'post': self.client.get(
                reverse('blog:post_detail', kwargs={'slug': _SAFE_POST_SLUG}),
            ),
        }
        html = {}
        for label, response in pages.items():
            self.assertEqual(response.status_code, 200, label)
            html[label] = response.content.decode()
        return html

    def _hidden_post_url(self):
        return reverse('blog:post_detail', kwargs={'slug': _HIDDEN_POST_SLUG})

    def _category_url(self):
        return reverse('blog:category', kwargs={'category_slug': 'perekazy'})

    def _assert_service_hrefs(self, html, label, present):
        for _title, slug, _desc in _SEO_HIDDEN_SERVICES:
            needle = f'#svc-{slug}'
            if present:
                self.assertIn(needle, html, label)
            else:
                self.assertNotIn(needle, html, label)

    def test_mode_off_keeps_hidden_service_links_and_transfer_copy(self):
        self._set_mode(False)
        pages = self._pages()
        hidden_post = self._hidden_post_url()
        for label, html in pages.items():
            self._assert_service_hrefs(html, label, True)
            self.assertIn(hidden_post, html, label)
            self.assertIn('переказ', html.lower(), label)
            self.assertIn('swift', html.lower(), label)
        home = pages['home']
        self.assertIn('SWIFT-перекази', home)
        self.assertIn('Грошові перекази', home)
        self.assertIn('promo-swift.png', home)
        self.assertIn('aria-label="SWIFT"', home)
        self.assertIn('aria-label="Перекази"', home)
        self.assertIn('#svc-obmin-valyut', home)
        services = pages['services']
        self.assertIn(_HERO_TRANSFER, services)
        self.assertIn('svc-hero__lead', services)
        self.assertIn(_BLOCK_TRANSFER, services)
        self.assertIn('#svc-obmin-valyut', services)
        blog = pages['blog']
        self.assertIn('Перекази', blog)
        self.assertIn(self._category_url(), blog)
        self.assertIn(_HIDDEN_POST_TITLE, blog)
        self.assertIn(_SAFE_POST_TITLE, blog)
        self.assertIn('Курси', blog)
        post = pages['post']
        self.assertIn(_HIDDEN_POST_TITLE, post)
        self.assertIn(_SAFE_POST_TITLE, post)
        self.assertIn('#svc-obmin-valyut', post)

    def test_mode_on_omits_hidden_service_links_and_transfer_words(self):
        self._set_mode(True)
        pages = self._pages()
        hidden_post = self._hidden_post_url()
        category = self._category_url()
        for label, html in pages.items():
            self._assert_service_hrefs(html, label, False)
            self.assertNotIn(hidden_post, html, label)
            self.assertNotIn(category, html, label)
            self.assertNotIn(_HIDDEN_POST_TITLE, html, label)
            self.assertNotIn('Перекази', html, label)
            self.assertNotIn('promo-swift.png', html, label)
            self.assertNotIn('SWIFT-перекази', html, label)
            self.assertNotIn(_BLOCK_TRANSFER, html, label)
            self.assertNotIn(_HERO_TRANSFER, html, label)
            self.assertIn('#svc-obmin-valyut', html, label)
            self.assertIn(_SAFE_POST_TITLE, html, label)
            _assert_no_transfer_words(self, html, label)
            self.assertNotIn('display:none', ''.join(html.lower().split()), label)
        self.assertIn('USD та EUR', pages['home'])
        self.assertIn('bills.png', pages['home'])
        self.assertNotIn('svc-hero__lead', pages['services'])
        self.assertIn('Курси', pages['blog'])
        self.assertNotIn('Купуйте та продавайте понад 15 валют', pages['services'])


_TITLE_SEO = 'ZZ-SEO-КРИПТОВАЛЮТА'
_TITLE_PAGE = 'ZZ-PAGE-ЗОЛОТО-ПЕРЕКАЗИ'
_DOC_MODE = 'ZZ-SEO-MODE'
_TITLE_SITE = 'ZZ-SITE'
_TITLE_ONLY = 'ZZ-ONLY-TITLE-MODE'

_BRANDED_TITLES = (
    ('content:services', ServicesPage),
    ('content:advantages', AdvantagesPage),
    ('content:faq', FaqPage),
    ('network:city_list', CitiesPage),
    ('blog:post_list', BlogPage),
    ('rates:rates_page', RatesPage),
)

_PLAIN_TITLES = (
    ('content:contacts', ContactsPage),
    ('content:privacy', PrivacyPage),
    ('reviews:review_list', ReviewsPage),
)


class ExchangeOnlyDocumentTitleTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        settings = SiteSettings.load()
        settings.site_name = _TITLE_SITE
        settings.exchange_only = False
        settings.save()
        cache.clear()

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

    def _title_of(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        match = re.search(r'<title>(.*?)</title>', response.content.decode(), re.DOTALL)
        self.assertIsNotNone(match, url)
        return match.group(1).strip()

    def _fill(self, model, seo=_TITLE_SEO, mode=''):
        page = model.load()
        _blank_text_modes(page)
        page.seo_title = seo
        page.seo_title_mode = mode
        page.title = _TITLE_PAGE
        page.save()
        return page

    def _assert_closed(self, url, expected):
        title = self._title_of(url)
        self.assertEqual(title, expected)
        self.assertIn(_TITLE_SITE, title)
        self.assertNotIn(_TITLE_SEO, title)
        self.assertNotIn(_TITLE_PAGE, title)
        self.assertNotIn(NEUTRAL_DESCRIPTION, title)
        for token in ('КРИПТОВАЛЮТА', 'ЗОЛОТО', 'ПЕРЕКАЗИ'):
            self.assertNotIn(token, title)
        return title

    def test_home_title(self):
        page = HomePage.load()
        _blank_text_modes(page)
        page.seo_title = _TITLE_SEO
        page.save()
        url = reverse('core:home')
        self._set_mode(False)
        self.assertEqual(self._title_of(url), _TITLE_SEO)
        self._set_mode(True)
        self._assert_closed(url, _TITLE_SITE)
        page.seo_title_mode = _DOC_MODE
        page.save()
        self._set_mode(True)
        title = self._title_of(url)
        self.assertEqual(title, _DOC_MODE)
        self.assertNotIn(_TITLE_SEO, title)
        self.assertNotIn(NEUTRAL_DESCRIPTION, title)

    def test_home_empty_seo_stays_site_name(self):
        page = HomePage.load()
        _blank_text_modes(page)
        page.seo_title = ''
        page.save()
        url = reverse('core:home')
        self._set_mode(False)
        self.assertEqual(self._title_of(url), _TITLE_SITE)
        self._set_mode(True)
        self._assert_closed(url, _TITLE_SITE)

    def test_branded_pages(self):
        for url_name, model in _BRANDED_TITLES:
            with self.subTest(url=url_name):
                self._fill(model)
                url = reverse(url_name)
                self._set_mode(False)
                self.assertEqual(
                    self._title_of(url),
                    f'{_TITLE_SEO} · {_TITLE_SITE}',
                )
                self._set_mode(True)
                self._assert_closed(url, _TITLE_SITE)
                self._fill(model, mode=_DOC_MODE)
                self._set_mode(True)
                title = self._title_of(url)
                self.assertEqual(title, f'{_DOC_MODE} · {_TITLE_SITE}')
                self.assertIn(_DOC_MODE, title)
                self.assertNotIn(_TITLE_SEO, title)
                self.assertNotIn(_TITLE_PAGE, title)
                self.assertNotIn(NEUTRAL_DESCRIPTION, title)

    def test_empty_seo_title_off_uses_page_title(self):
        page = ServicesPage.load()
        _blank_text_modes(page)
        page.seo_title = ''
        page.title = _TITLE_PAGE
        page.save()
        url = reverse('content:services')
        self._set_mode(False)
        self.assertEqual(self._title_of(url), f'{_TITLE_PAGE} · {_TITLE_SITE}')
        self._set_mode(True)
        self._assert_closed(url, _TITLE_SITE)

    def test_title_mode_when_seo_mode_empty(self):
        page = self._fill(FaqPage, mode='')
        page.title_mode = _TITLE_ONLY
        page.save(update_fields=['title_mode'])
        url = reverse('content:faq')
        self._set_mode(True)
        title = self._title_of(url)
        self.assertEqual(title, f'{_TITLE_ONLY} · {_TITLE_SITE}')
        self.assertNotIn(_TITLE_SEO, title)
        self.assertNotIn(_TITLE_PAGE, title)
        page.seo_title_mode = _DOC_MODE
        page.save(update_fields=['seo_title_mode'])
        title = self._title_of(url)
        self.assertEqual(title, f'{_DOC_MODE} · {_TITLE_SITE}')
        self.assertNotIn(_TITLE_ONLY, title)

    def test_city_detail(self):
        city = City.objects.create(
            name='Львів',
            slug='lviv-title',
            seo_title=_TITLE_SEO,
            seo_title_mode='',
        )
        url = reverse('network:city_detail', kwargs={'slug': city.slug})
        self._set_mode(False)
        self.assertEqual(self._title_of(url), f'{_TITLE_SEO} · {_TITLE_SITE}')
        self._set_mode(True)
        self._assert_closed(url, _TITLE_SITE)
        self.assertNotIn('Львів', self._title_of(url))
        city.seo_title = ''
        city.seo_title_mode = ''
        city.save()
        self._set_mode(False)
        self.assertEqual(self._title_of(url), f'Львів · {_TITLE_SITE}')
        self._set_mode(True)
        title = self._title_of(url)
        self.assertEqual(title, _TITLE_SITE)
        self.assertNotIn('Львів', title)
        city.seo_title = _TITLE_SEO
        city.seo_title_mode = _DOC_MODE
        city.save()
        self._set_mode(True)
        title = self._title_of(url)
        self.assertEqual(title, f'{_DOC_MODE} · {_TITLE_SITE}')
        self.assertNotIn(_TITLE_SEO, title)
        self.assertNotIn('Львів', title)

    def test_pages_without_mode_columns(self):
        for url_name, model in _PLAIN_TITLES:
            with self.subTest(url=url_name):
                page = model.load()
                _blank_text_modes(page)
                page.seo_title = _TITLE_SEO
                page.title = _TITLE_PAGE
                page.save()
                url = reverse(url_name)
                self._set_mode(False)
                self.assertEqual(
                    self._title_of(url),
                    f'{_TITLE_SEO} · {_TITLE_SITE}',
                )
                self._set_mode(True)
                self._assert_closed(url, _TITLE_SITE)

    def test_blog_category_ignores_view_title(self):
        self._fill(BlogPage, mode='')
        category = Category.objects.create(name='ZZ-CAT-NAME', slug='zz-cat-title')
        Post.objects.create(
            category=category,
            title='Курс у касі',
            slug='zz-cat-title-post',
            body='Текст про курс.',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        url = reverse('blog:category', kwargs={'category_slug': category.slug})
        self._set_mode(False)
        self.assertEqual(self._title_of(url), f'ZZ-CAT-NAME · {_TITLE_SITE}')
        self._set_mode(True)
        title = self._title_of(url)
        self.assertEqual(title, _TITLE_SITE)
        self.assertNotIn('ZZ-CAT-NAME', title)
        self.assertNotIn(_TITLE_SEO, title)
        self.assertNotIn(NEUTRAL_DESCRIPTION, title)

    def test_post_and_pair(self):
        category = Category.objects.create(name='Нотатки', slug='notatky-title')
        post = Post.objects.create(
            category=category,
            title=_TITLE_PAGE,
            slug='zz-title-post',
            body='Текст про курс.',
            seo_title=_TITLE_SEO,
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        pair = CurrencyPair.objects.create(
            code='CHF',
            name='Франк',
            slug='chf-title',
            seo_title=_TITLE_SEO,
            exchange_safe=True,
        )
        post_url = reverse('blog:post_detail', kwargs={'slug': post.slug})
        pair_url = reverse('rates:pair_detail', kwargs={'slug': pair.slug})
        self._set_mode(False)
        self.assertEqual(self._title_of(post_url), f'{_TITLE_SEO} · {_TITLE_SITE}')
        self.assertEqual(self._title_of(pair_url), f'{_TITLE_SEO} · {_TITLE_SITE}')
        self._set_mode(True)
        self._assert_closed(post_url, _TITLE_SITE)
        self._assert_closed(pair_url, _TITLE_SITE)
        pair.seo_title = ''
        pair.save()
        self._set_mode(False)
        self.assertEqual(self._title_of(pair_url), f'CHF · {_TITLE_SITE}')
        self._set_mode(True)
        title = self._title_of(pair_url)
        self.assertEqual(title, _TITLE_SITE)
        self.assertNotIn('CHF', title)


_ROOT = Path(__file__).resolve().parents[3]
_LAYOUT_H1 = 'Криптовалюта для початківців:'
_LAYOUT_H1B = 'BTC і USDT'
_LAYOUT_LEAD = 'цифровим золотом'
_LAYOUT_READ = '6 хв читання'
_LAYOUT_SEC = 'Що таке біткоїн'
_MODE_H1 = 'Готівковий заголовок'
_MODE_LEAD = 'Фіксація курсу у касі'
_BLOCK_TEXT_MODE = 'Готівковий опис каси'
_BLOCK_POINT_MODE = 'Долар у відділенні'
_BLOCK_CTA_MODE = 'Забронювати готівку'
_ARTICLES_LEAD_MODE = 'Статті про готівковий курс у касі'
_BARE_TITLE = 'ZZ-PAGE-ЗОЛОТО-ПЕРЕКАЗИ'
_BARE_SITE = 'ZZ-BARE-SITE'


def _class_attrs(model, **attrs):
    for name in attrs:
        try:
            model._meta.get_field(name)
        except FieldDoesNotExist:
            continue
        raise AssertionError(f'{model.__name__}.{name} is a real column')
    for name, value in attrs.items():
        setattr(model, name, value)


def _clear_attrs(model, attrs):
    for name in attrs:
        if name in model.__dict__:
            delattr(model, name)


class ExchangeOnlyBareTitleTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        settings = SiteSettings.load()
        settings.site_name = _BARE_SITE
        settings.exchange_only = False
        settings.save()
        cache.clear()

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

    def _html(self):
        request = RequestFactory().get('/bare-title/')
        return render_to_string(
            'base.html',
            {'page_title': _BARE_TITLE},
            request=request,
        )

    def _title(self, html):
        match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
        self.assertIsNotNone(match)
        return match.group(1).strip()

    def test_mode_without_page_title_is_only_site_name(self):
        self._set_mode(False)
        off = self._html()
        self.assertEqual(self._title(off), f'{_BARE_TITLE} · {_BARE_SITE}')
        self._set_mode(True)
        on = self._html()
        title = self._title(on)
        self.assertEqual(title, _BARE_SITE)
        self.assertNotIn(_BARE_TITLE, on)
        self.assertNotIn('ЗОЛОТО', on)
        self.assertNotIn('ПЕРЕКАЗИ', on)
        self.assertNotIn(NEUTRAL_DESCRIPTION, title)


class ExchangeOnlyArticleLayoutTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        category = Category.objects.create(name='Каса', slug='kasa-layout')
        self.post = Post.objects.create(
            category=category,
            title='Нотатка про касу',
            slug='kryptovalyuta-btc-usdt',
            excerpt='',
            body='',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
            published_at=timezone.now(),
        )

    def tearDown(self):
        _clear_attrs(Post, ('h1a_mode', 'h1b_mode', 'lead_mode'))
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _set_mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def _article(self, html):
        start = html.index('data-qa="post-detail"')
        finish = html.index('article-body__nav', start)
        return html[start:finish]

    def test_layout_mode_replaces_hardcoded_article(self):
        url = reverse('blog:post_detail', kwargs={'slug': self.post.slug})
        self._set_mode(False)
        off = self.client.get(url)
        self.assertEqual(off.status_code, 200)
        off_html = off.content.decode()
        article = self._article(off_html)
        self.assertIn(_LAYOUT_H1, article)
        self.assertIn(_LAYOUT_H1B, article)
        self.assertIn(_LAYOUT_LEAD, article)
        self.assertIn(_LAYOUT_READ, article)
        self.assertIn(_LAYOUT_SEC, article)
        self.assertIn(f'article-banner__title">{_LAYOUT_H1}', article)

        self._set_mode(True)
        on = self.client.get(url)
        self.assertEqual(on.status_code, 200)
        on_html = on.content.decode()
        on_article = self._article(on_html)
        for token in (_LAYOUT_H1, _LAYOUT_H1B, _LAYOUT_LEAD, _LAYOUT_READ, _LAYOUT_SEC, 'USDT', 'біткоїн'):
            self.assertNotIn(token, on_html, token)
        self.assertNotIn('article-sec', on_article)
        self.assertNotIn('article-banner__title', on_article)

        _class_attrs(
            Post,
            h1a_mode=_MODE_H1,
            h1b_mode='долар',
            lead_mode=_MODE_LEAD,
        )
        try:
            filled = self.client.get(url).content.decode()
            filled_article = self._article(filled)
            self.assertIn(_MODE_H1, filled_article)
            self.assertIn(_MODE_LEAD, filled_article)
            self.assertNotIn(_LAYOUT_H1, filled)
            self.assertNotIn(_LAYOUT_SEC, filled)
            self._set_mode(False)
            restored = self.client.get(url).content.decode()
            self.assertIn(_LAYOUT_H1, self._article(restored))
            self.assertNotIn(_MODE_H1, restored)
            self.assertNotIn(_MODE_LEAD, restored)
        finally:
            _clear_attrs(Post, ('h1a_mode', 'h1b_mode', 'lead_mode'))


class ExchangeOnlyNavBannerTests(TestCase):
    def test_nav_hides_banner_from_event_without_inline_style(self):
        script = (_ROOT / 'src/core/static/js/nav.js').read_text(encoding='utf-8')
        base = (_ROOT / 'templates/base.html').read_text(encoding='utf-8')
        self.assertIn('bannerHidden', script)
        self.assertIn("setAttribute('hidden'", script)
        self.assertIn('detail.bannerTitle', script)
        self.assertIn('detail.bannerText', script)
        self.assertNotIn('.style', script)
        self.assertIn("{% static 'js/nav.js' %}?v=16", base)
        self.assertNotIn("{% static 'js/nav.js' %}?v=15", base)


class ExchangeOnlyEmptyStatsTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = HomePage.load()
        page.show_why = True
        page.save()
        HomeStat.objects.all().delete()

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

    def test_empty_home_stats_fallback_hidden_in_mode(self):
        self._set_mode(False)
        off = self.client.get(reverse('core:home'))
        self.assertEqual(off.status_code, 200)
        off_html = off.content.decode()
        self.assertEqual(off.context['home_stats'], [])
        self.assertIn('7K', off_html)
        self.assertIn('Постійних клієнтів', off_html)
        self._set_mode(True)
        on = self.client.get(reverse('core:home'))
        self.assertEqual(on.status_code, 200)
        on_html = on.content.decode()
        self.assertEqual(on.context['home_stats'], [])
        self.assertNotIn('7K', on_html)
        self.assertNotIn('Постійних клієнтів', on_html)
        self.assertNotIn('display:none', ''.join(on_html.lower().split()))


class ExchangeOnlyServiceBlockModeTests(ExchangeTemplateCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = ServicesPage.load()
        page.intro = ''
        page.intro_mode = ''
        page.save()
        home = HomePage.load()
        home.articles_lead_mode = _ARTICLES_LEAD_MODE
        home.save()
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut',
            short_desc='Короткий опис каси',
            exchange_safe=True,
            sort_order=1,
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

    def test_mode_fields_replace_service_blocks_and_articles_lead(self):
        Service.objects.filter(slug='obmin-valyut').update(
            block_text_mode=_BLOCK_TEXT_MODE,
            block_points_mode=_BLOCK_POINT_MODE + '\nЄвро у касі',
            block_cta_mode=_BLOCK_CTA_MODE,
        )
        self._set_mode(False)
        off = self.client.get(reverse('content:services'))
        self.assertEqual(off.status_code, 200)
        off_html = off.content.decode()
        self.assertIn('Купуйте та продавайте понад 15 валют', off_html)
        self.assertIn('Без прихованих комісій', off_html)
        self.assertIn('Зафіксувати курс', off_html)
        self.assertIn(_SERVICES_LEAD, off_html)
        self.assertNotIn(_BLOCK_TEXT_MODE, off_html)
        self.assertNotIn(_BLOCK_POINT_MODE, off_html)
        self.assertNotIn(_BLOCK_CTA_MODE, off_html)
        self.assertNotIn(_ARTICLES_LEAD_MODE, off_html)

        self._set_mode(True)
        on = self.client.get(reverse('content:services'))
        self.assertEqual(on.status_code, 200)
        on_html = on.content.decode()
        self.assertIn(_BLOCK_TEXT_MODE, on_html)
        self.assertIn(_BLOCK_POINT_MODE, on_html)
        self.assertIn('Євро у касі', on_html)
        self.assertIn(_BLOCK_CTA_MODE, on_html)
        self.assertIn(_ARTICLES_LEAD_MODE, on_html)
        self.assertNotIn('Купуйте та продавайте понад 15 валют', on_html)
        self.assertNotIn('Без прихованих комісій', on_html)
        self.assertNotIn('USD, EUR, PLN', on_html)
        self.assertNotIn('Зафіксувати курс', on_html)
        self.assertNotIn(_SERVICES_LEAD, on_html)
        self.assertNotIn('Короткий опис каси', on_html)
        self.assertNotIn('display:none', ''.join(on_html.lower().split()))
