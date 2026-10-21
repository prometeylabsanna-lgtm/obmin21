import os
import re
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.blog.models import Category, Post
from src.content.models import AdvantagesPage, FaqItem, HomePage, Service, ServicesPage
from src.core.models import SiteSettings
from src.network.models import Branch, City

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


class ExchangeOnlyServicesCityTemplateTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = ServicesPage.load()
        page.intro = _RAW_INTRO
        page.intro_mode = _INTRO_MODE
        page.seo_description = 'Курси готівки у відділеннях.'
        page.save()
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


class ExchangeOnlySeoLinksTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = ServicesPage.load()
        page.seo_title = 'Послуги обміну валют'
        page.seo_description = 'Готівковий обмін долара та євро у відділеннях.'
        page.save()
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
