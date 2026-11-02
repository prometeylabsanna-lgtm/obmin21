import re
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import Service
from src.core.models import SiteSettings
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard

_LONG = 'А' * 80
_ADDRESS = 'Б' * 180


def _visible(html):
    text = re.sub(r'<script\b[^>]*>.*?</script>', ' ', html, flags=re.I | re.S)
    text = re.sub(r'<style\b[^>]*>.*?</style>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    return text


class EdgeLayoutTests(TestCase):
    def setUp(self):
        cache.clear()
        site = SiteSettings.load()
        site.default_phone = ''
        site.telegram_url = ''
        site.save()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _clean(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        html = response.content.decode()
        self.assertNotIn('>None<', html, url)
        self.assertNotIn('src=""', html, url)
        self.assertNotIn('href="tel:"', html, url)
        self.assertNotRegex(_visible(html), r'\bNone\b', url)
        return html

    def test_city_without_branches(self):
        city = City.objects.create(
            name='Черкаси',
            slug='cherkasy-empty',
            phone='',
            sort_order=0,
        )
        pages = (
            reverse('core:home'),
            reverse('content:contacts'),
            reverse('network:city_detail', kwargs={'slug': city.slug}),
        )
        for url in pages:
            html = self._clean(url)
            if url.endswith(city.slug + '/'):
                self.assertIn('Відділення зʼявляться незабаром', html)
                self.assertNotIn('class="card"', html)
        home = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('<iframe', home)
        self.assertNotIn('map-section__label">Телефон:', home)

    def test_branch_without_coords_or_phone(self):
        city = City.objects.create(
            name='Луцьк',
            slug='lutsk-nocoords',
            phone='',
            sort_order=0,
        )
        branch = Branch.objects.create(
            city=city,
            name='Центр',
            address='вул. Лесі Українки, 15',
            phone='',
            lat=None,
            lng=None,
        )
        pages = (
            reverse('core:home'),
            reverse('content:contacts'),
            reverse('network:city_detail', kwargs={'slug': city.slug}),
        )
        for url in pages:
            html = self._clean(url)
            self.assertIn(branch.address, html, url)
            self.assertNotIn('map-section__label">Телефон:', html, url)
            self.assertNotIn('>Телефон</div>\n        <div class="contacts-card__value"></div>', html)
        home = self.client.get(reverse('core:home')).content.decode()
        iframe = re.search(r'<iframe\b([^>]*)>', home, re.S)
        self.assertIsNotNone(iframe)
        src = re.search(r'\bsrc="([^"]+)"', iframe.group(1))
        self.assertIsNotNone(src)
        self.assertTrue(src.group(1).startswith('https://'))
        contacts = self.client.get(reverse('content:contacts')).content.decode()
        frame = re.search(r'<iframe\b([^>]*)>', contacts, re.S)
        self.assertIsNotNone(frame)
        frame_src = re.search(r'\bsrc="([^"]+)"', frame.group(1))
        self.assertIsNotNone(frame_src)
        link = re.search(r'data-branches-link[^>]*href="([^"]+)"', contacts)
        if link is None:
            link = re.search(r'href="([^"]+)"[^>]*data-branches-link', contacts)
        self.assertIsNotNone(link)
        self.assertTrue(link.group(1).startswith('https://'))

    def test_city_without_quotes_has_empty_state(self):
        City.objects.create(name='Рівне', slug='rivne-norates', phone='', sort_order=0)
        for url in (reverse('core:home'), reverse('rates:rates_page')):
            html = self._clean(url)
            self.assertIn('Немає курсів для цієї вкладки', html, url)
            self.assertNotIn('rates-table__head', html, url)
            self.assertNotIn('rates-table__row', html, url)

    def test_missing_images_do_not_render_empty_src(self):
        city = City.objects.create(name='Тернопіль', slug='ternopil-img', phone='', sort_order=0)
        self.assertFalse(city.banner_image)
        pair = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-edge')
        self.assertFalse(pair.flag_image)
        Quote.objects.create(
            pair=pair,
            board=RateBoard.RETAIL,
            city=city,
            buy=Decimal('41.20'),
            sell=Decimal('41.80'),
        )
        Service.objects.create(title='Обмін', slug='obmin-edge', short_desc='Каса')
        category = Category.objects.create(name='Новини', slug='novyny-edge')
        Post.objects.create(
            category=category,
            title='Стаття без фото',
            slug='statti-bez-foto',
            body='Текст',
            status=Post.Status.PUBLISHED,
        )
        for url in (
            reverse('core:home'),
            reverse('content:services'),
            reverse('blog:post_list'),
            reverse('rates:rates_page'),
            reverse('blog:post_detail', kwargs={'slug': 'statti-bez-foto'}),
        ):
            html = self._clean(url)
            self.assertNotRegex(html, r'<img\b[^>]*\bsrc=""')

    def test_long_names_stay_in_markup_and_css_wraps(self):
        city = City.objects.create(
            name=_LONG,
            slug='dovha-nazva',
            phone='',
            sort_order=0,
        )
        Branch.objects.create(
            city=city,
            name=_LONG,
            address=_ADDRESS,
            phone='',
        )
        Service.objects.create(title=_LONG, slug='dovha-posluga', short_desc='Каса')
        pages = (
            reverse('core:home'),
            reverse('content:contacts'),
            reverse('network:city_detail', kwargs={'slug': city.slug}),
            reverse('content:services'),
        )
        for url in pages:
            html = self._clean(url)
            self.assertIn(_LONG, html, url)
        home = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(_ADDRESS, home)
        css_root = settings.BASE_DIR / 'src/core/static/css/components'
        for name in ('cards.css', 'home.css', 'contacts.css', 'pages.css'):
            css = (css_root / name).read_text(encoding='utf-8')
            self.assertIn('overflow-wrap: anywhere', css, name)
            self.assertIn('min-width: 0', css, name)
            self.assertNotIn('!important', css, name)
        header = (css_root / 'header.css').read_text(encoding='utf-8')
        label = re.search(
            r'\.city-select__btn \[data-city-label\] \{([^}]+)\}',
            header,
        )
        self.assertIsNotNone(label)
        block = label.group(1)
        self.assertIn('text-overflow: ellipsis', block)
        self.assertIn('white-space: nowrap', block)
