import json
import re
import tempfile
from decimal import Decimal
from html import unescape
from io import BytesIO

from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from src.blog.article_data import layout_for
from src.blog.models import Category, Post
from src.blog.views import category_page_copy
from src.content.models import AdvantagesPage, FaqItem, ServicesPage
from src.core.seo_words import contains_stop_word
from src.core.tests.test_eo_default_mode import forced_exchange_client
from src.core.tests.test_seo_public import _graph, _ld_types
from src.network.models import Branch, City

_Q_RE = re.compile(
    r'<button[^>]*class="faq-card__q"[^>]*>\s*<span>(.*?)</span>',
    re.S,
)


def _png(width, height):
    buf = BytesIO()
    Image.new('RGB', (width, height), (20, 40, 60)).save(buf, format='PNG')
    return SimpleUploadedFile('shot.png', buf.getvalue(), content_type='image/png')


def _visible_questions(html):
    return [unescape(item) for item in _Q_RE.findall(html)]


def _faq_node(html):
    payload = _graph(html)[0]
    nodes = [node for node in payload['@graph'] if node.get('@type') == 'FAQPage']
    if not nodes:
        return None
    return nodes[0]


def _faq_names(html):
    node = _faq_node(html)
    if node is None:
        return None
    return [item['name'] for item in node['mainEntity']]


def _business(html):
    payload = _graph(html)[0]
    return next(
        node for node in payload['@graph']
        if str(node.get('@id', '')).endswith('#business')
    )


class _Meta:
    def __init__(self, names):
        self._names = set(names)

    def get_field(self, name):
        if name not in self._names:
            raise FieldDoesNotExist(name)


class _SeoRow:
    def __init__(self, **kwargs):
        self._meta = _Meta(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)


class FaqSchemaTests(TestCase):
    def _pages(self, client):
        pages = {}
        for url in ('/', '/faq/', '/posluhy/'):
            response = client.get(url)
            self.assertEqual(response.status_code, 200, url)
            pages[url] = response.content.decode()
        return pages

    def test_json_ld_matches_visible_questions_in_both_modes(self):
        FaqItem.objects.create(
            question='Неактивне питання про курс',
            answer='Його не видно.',
            is_active=False,
            exchange_safe=True,
            sort_order=0,
        )
        for index in range(1, 10):
            FaqItem.objects.create(
                question=f'Питання про касу {index}',
                answer=f'Відповідь каси {index}.',
                is_active=True,
                exchange_safe=True,
                sort_order=index,
            )
        FaqItem.objects.create(
            question='Як надіслати переказ SWIFT?',
            answer='Це прихована відповідь про криптовалюту.',
            is_active=True,
            exchange_safe=False,
            sort_order=20,
        )
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                with forced_exchange_client(enabled) as client:
                    pages = self._pages(client)
                home_names = _faq_names(pages['/'])
                faq_names = _faq_names(pages['/faq/'])
                self.assertEqual(home_names, _visible_questions(pages['/']))
                self.assertEqual(faq_names, _visible_questions(pages['/faq/']))
                self.assertNotIn('Неактивне питання про курс', home_names)
                self.assertEqual(len(home_names), 8)
                self.assertGreater(len(faq_names), len(home_names))
                self.assertNotIn('FAQPage', _ld_types(pages['/posluhy/']))
                self.assertIn('<h1 class="faq-section__title">', pages['/faq/'])
                self.assertNotIn('<h2 class="faq-section__title">', pages['/faq/'])
                self.assertIn('<h2 class="faq-section__title">', pages['/'])
                self.assertNotIn('<h1 class="faq-section__title">', pages['/'])
                if enabled:
                    raw = json.dumps(_faq_node(pages['/faq/']), ensure_ascii=False)
                    self.assertFalse(contains_stop_word(raw), raw)
                    self.assertNotIn('SWIFT', raw)
                    self.assertNotIn('криптовалюту', raw)
                else:
                    self.assertIn('Як надіслати переказ SWIFT?', faq_names)


class CategorySeoTests(TestCase):
    def test_page_uses_category_name_when_seo_fields_are_absent(self):
        category = Category.objects.create(name='ZZ-RUBRYKA', slug='zz-rubryka')
        Post.objects.create(
            category=category,
            title='Нотатка',
            slug='zz-rubryka-post',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
            published_at=timezone.now(),
        )
        url = '/blog/kategoriya/zz-rubryka/'
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                with forced_exchange_client(enabled) as client:
                    response = client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertRegex(html, r'<h1 class="blog-hero__title">ZZ-RUBRYKA</h1>')
                self.assertRegex(html, r'<title>\s*ZZ-RUBRYKA · Обмін21\s*</title>')
                self.assertEqual(
                    response.context['page_description'],
                    'Статті рубрики ZZ-RUBRYKA.',
                )
                self.assertIn(
                    '<meta name="description" content="Статті рубрики ZZ-RUBRYKA.">',
                    html,
                )

    def test_copy_prefers_seo_fields_when_the_model_has_them(self):
        plain = _SeoRow(
            name='Каса',
            seo_title='SEO каса',
            seo_description='Опис каса',
        )
        with forced_exchange_client(False):
            copy = category_page_copy(plain, None)
        self.assertEqual(copy['heading'], 'Каса')
        self.assertEqual(copy['title'], 'SEO каса')
        self.assertEqual(copy['description'], 'Опис каса')
        with forced_exchange_client(True):
            mode_off_fields = category_page_copy(plain, None)
        self.assertEqual(mode_off_fields['title'], 'Каса')
        self.assertEqual(mode_off_fields['description'], 'Статті рубрики Каса.')
        filled = _SeoRow(
            name='Каса',
            seo_title='SEO каса',
            seo_description='Опис каса',
            seo_title_mode='Режим каса',
            seo_description_mode='Опис режиму каса',
        )
        with forced_exchange_client(True):
            mode_copy = category_page_copy(filled, None)
        self.assertEqual(mode_copy['heading'], 'Каса')
        self.assertEqual(mode_copy['title'], 'Режим каса')
        self.assertEqual(mode_copy['description'], 'Опис режиму каса')


class ImageSizeTests(TestCase):
    def test_article_body_services_hero_and_exchange_coins_use_real_size(self):
        category = Category.objects.create(name='Розміри', slug='rozmiry')
        layout_post = Post.objects.create(
            category=category,
            title='Долар чи євро',
            slug='dolar-chy-yevro',
            body='',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
            published_at=timezone.now(),
        )
        layout = layout_for(layout_post)
        self.assertGreater(layout['fig_width'], 0)
        self.assertGreater(layout['fig_height'], 0)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                figure_post = Post.objects.create(
                    category=category,
                    title='Каса',
                    slug='kasa-rozmir',
                    body='Абзац про відділення.',
                    status=Post.Status.PUBLISHED,
                    exchange_safe=True,
                    published_at=timezone.now(),
                    figure=_png(40, 25),
                )
                services = ServicesPage.load()
                services.hero_image.save('hero.png', _png(30, 18), save=True)
                advantages = AdvantagesPage.load()
                advantages.why_coins_mode.save('coins.png', _png(22, 14), save=True)
                figure_post.refresh_from_db()
                services.refresh_from_db()
                advantages.refresh_from_db()
                figure_size = (figure_post.figure.width, figure_post.figure.height)
                hero_size = (services.hero_image.width, services.hero_image.height)
                coin_size = (advantages.why_coins_mode.width, advantages.why_coins_mode.height)
                article = self.client.get('/blog/dolar-chy-yevro/').content.decode()
                body = self.client.get('/blog/kasa-rozmir/').content.decode()
                hero = self.client.get('/posluhy/').content.decode()
                with forced_exchange_client(True) as client:
                    coins = client.get('/perevahy/').content.decode()
        self.assertRegex(
            article,
            rf'width="{layout["fig_width"]}" height="{layout["fig_height"]}"',
        )
        self.assertIn(f'width="{figure_size[0]}" height="{figure_size[1]}"', body)
        self.assertEqual(figure_size, (40, 25))
        self.assertIn(f'width="{hero_size[0]}" height="{hero_size[1]}"', hero)
        self.assertEqual(hero_size, (30, 18))
        self.assertIn('class="why-adv__coins"', coins)
        self.assertIn(f'width="{coin_size[0]}" height="{coin_size[1]}"', coins)
        self.assertEqual(coin_size, (22, 14))


class BranchSchemaTests(TestCase):
    def test_departments_use_only_filled_branch_fields(self):
        kyiv = City.objects.create(
            name='Київ базове',
            name_mode='Київ каса',
            slug='kyiv-schema',
            is_active=True,
            sort_order=0,
        )
        lviv = City.objects.create(
            name='Львів базове',
            name_mode='Львів каса',
            slug='lviv-schema',
            is_active=True,
            sort_order=1,
        )
        closed = City.objects.create(
            name='Закрите',
            slug='zakryte-schema',
            is_active=False,
        )
        Branch.objects.create(
            city=kyiv,
            address='вул. Миру, 1',
            hours='Щодня 8:00-21:00',
            phone='+380441110001',
            lat=Decimal('50.450000'),
            lng=Decimal('30.523000'),
            is_active=True,
            sort_order=1,
        )
        Branch.objects.create(
            city=kyiv,
            address='Обмін криптовалюти',
            hours='swift 9-18',
            is_active=True,
            sort_order=2,
        )
        Branch.objects.create(
            city=lviv,
            address='вул. Ринкова, 2',
            hours='',
            phone='',
            lat=None,
            lng=Decimal('24.030000'),
            is_active=True,
            sort_order=1,
        )
        Branch.objects.create(
            city=kyiv,
            address='вул. Закрита, 3',
            hours='9-18',
            lat=Decimal('50.450000'),
            lng=Decimal('30.523000'),
            is_active=False,
        )
        Branch.objects.create(
            city=closed,
            address='вул. Немає, 4',
            hours='9-18',
            is_active=True,
        )
        for enabled, locality in ((False, 'Київ базове'), (True, 'Київ каса')):
            with self.subTest(enabled=enabled):
                with forced_exchange_client(enabled) as client:
                    html = client.get('/').content.decode()
                raw = re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    html,
                    re.S,
                ).group(1)
                business = _business(html)
                departments = business['department']
                self.assertNotIn('addressCountry', raw)
                self.assertNotIn('postalCode', raw)
                self.assertNotIn('addressRegion', raw)
                self.assertNotIn('dayOfWeek', raw)
                self.assertNotIn('вул. Закрита, 3', raw)
                self.assertNotIn('вул. Немає, 4', raw)
                full = departments[0]
                self.assertEqual(full['address']['streetAddress'], 'вул. Миру, 1')
                self.assertEqual(full['address']['addressLocality'], locality)
                self.assertEqual(full['openingHours'], 'Щодня 8:00-21:00')
                self.assertEqual(full['telephone'], '+380441110001')
                self.assertAlmostEqual(full['geo']['latitude'], 50.45, places=5)
                self.assertAlmostEqual(full['geo']['longitude'], 30.523, places=5)
                self.assertNotIn('addressCountry', full['address'])
                self.assertEqual(len(departments), 3)
                dirty = departments[1]
                if enabled:
                    self.assertNotIn('streetAddress', dirty.get('address', {}))
                    self.assertNotIn('openingHours', dirty)
                    self.assertEqual(dirty['address']['addressLocality'], 'Київ каса')
                    self.assertNotIn('криптовалюти', raw)
                    self.assertNotIn('swift', raw)
                    self.assertNotIn('Київ базове', raw)
                else:
                    self.assertEqual(dirty['address']['streetAddress'], 'Обмін криптовалюти')
                    self.assertEqual(dirty['openingHours'], 'swift 9-18')
                partial = departments[-1]
                self.assertEqual(partial['address']['streetAddress'], 'вул. Ринкова, 2')
                self.assertNotIn('openingHours', partial)
                self.assertNotIn('telephone', partial)
                self.assertNotIn('geo', partial)


class QueryCanonicalTests(TestCase):
    def test_city_and_direct_keep_paramless_canonical_and_robots_disallow(self):
        cases = (
            ('/?city=kyiv&direct=1', 'https://obmin21.com/'),
            ('/kursy/?direct=1', 'https://obmin21.com/kursy/'),
            ('/kontakty/?city=lviv', 'https://obmin21.com/kontakty/'),
        )
        for path, canonical in cases:
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                self.assertEqual(self.client.get(path).status_code, 200)
                self.assertIn(f'<link rel="canonical" href="{canonical}">', html)
                self.assertNotIn('?', html.split('rel="canonical"', 1)[1].split('>', 1)[0])
        robots = self.client.get('/robots.txt').content.decode()
        self.assertIn('Disallow: /*?*city=', robots)
        self.assertIn('Disallow: /*?*direct=', robots)
