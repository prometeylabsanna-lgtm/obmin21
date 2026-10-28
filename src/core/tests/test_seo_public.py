import json
import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from src.blog.models import Category, Post
from src.core.exchange_stopwords import matches_stop_words
from src.core.seo_words import contains_stop_word
from src.core.tests.test_eo_default_mode import forced_exchange_client
from src.reviews.models import Review

_SECRET = 'seo-audit-secret-panel'


def _ld_types(html):
    types = []

    def walk(node):
        if isinstance(node, dict):
            kind = node.get('@type')
            if isinstance(kind, str):
                types.append(kind)
            elif isinstance(kind, list):
                types.extend(str(item) for item in kind)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        re.S,
    ):
        walk(json.loads(block))
    return types


def _graph(html):
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        re.S,
    )
    return [json.loads(block) for block in blocks]


class SeoHeadTests(TestCase):
    def test_canonical_drops_query_and_matches_og_url(self):
        response = self.client.get('/kursy/?board=retail&sort=sell&utm_source=ads')
        html = response.content.decode()
        canonical = 'https://obmin21.com/kursy/'
        self.assertIn(f'<link rel="canonical" href="{canonical}">', html)
        self.assertIn(f'<meta property="og:url" content="{canonical}">', html)
        self.assertIn('<meta name="robots" content="noindex, follow">', html)
        self.assertNotIn('utm_source', html.split('og:url', 1)[0])

    def test_clean_url_is_indexable_and_has_og_image(self):
        html = self.client.get('/').content.decode()
        self.assertIn('<link rel="canonical" href="https://obmin21.com/">', html)
        self.assertNotIn('name="robots" content="noindex', html)
        self.assertIn('og-obmin21.webp', html)
        self.assertIn('<meta property="og:image:width" content="1200">', html)
        self.assertIn('<meta property="og:image:height" content="630">', html)
        self.assertNotIn('hreflang', html)
        image = Path(settings.BASE_DIR) / 'src/core/static/images/og-obmin21.webp'
        with Image.open(image) as opened:
            self.assertEqual(opened.size, (1200, 630))
            self.assertEqual(opened.format, 'WEBP')

    def test_schema_uses_financial_service_without_faq_or_offer(self):
        html = self.client.get('/faq/').content.decode()
        types = _ld_types(html)
        self.assertIn('Organization', types)
        self.assertIn('FinancialService', types)
        self.assertIn('LocalBusiness', types)
        self.assertNotIn('FAQPage', types)
        self.assertNotIn('Product', types)
        self.assertNotIn('Offer', types)

    def test_article_and_breadcrumbs_on_post(self):
        category = Category.objects.create(name='Поради', slug='porady')
        Post.objects.create(
            category=category,
            title='Курс долара',
            slug='kurs-dolara',
            excerpt='Фіксація курсу у відділенні.',
            body='Долар міняють у касі.',
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
            exchange_safe=True,
        )
        html = self.client.get('/blog/kurs-dolara/').content.decode()
        types = _ld_types(html)
        self.assertIn('Article', types)
        self.assertIn('BreadcrumbList', types)
        self.assertEqual(html.count('application/ld+json'), 1)
        self.assertIn('<meta property="og:type" content="article">', html)
        payload = _graph(html)[0]
        article = next(node for node in payload['@graph'] if node.get('@type') == 'Article')
        self.assertEqual(article['headline'], 'Курс долара')
        self.assertEqual(article['mainEntityOfPage'], 'https://obmin21.com/blog/kurs-dolara/')

    def test_rating_counts_only_visible_published_reviews(self):
        Review.objects.create(
            name='Олена',
            text='Обміняла долар у відділенні.',
            rating=5,
            is_published=True,
            exchange_safe=True,
            published_at=timezone.now(),
        )
        Review.objects.create(
            name='Ігор',
            text='криптовалюта gold swift переказ',
            rating=1,
            is_published=True,
            exchange_safe=False,
            published_at=timezone.now(),
        )
        Review.objects.create(
            name='Чернетка',
            text='Ще не опубліковано.',
            rating=2,
            is_published=False,
            exchange_safe=True,
            published_at=timezone.now(),
        )
        with forced_exchange_client(True) as client:
            html = client.get('/').content.decode()
        self.assertNotIn('криптовалюта', html)
        payload = _graph(html)[0]
        business = next(
            node for node in payload['@graph']
            if 'FinancialService' in node.get('@type', [])
        )
        self.assertEqual(business['aggregateRating']['reviewCount'], 1)
        self.assertEqual(business['aggregateRating']['ratingValue'], 5.0)
        self.assertNotIn('BTC', business.get('currenciesAccepted', ''))
        self.assertNotIn('USD, EUR, PLN', html)


class RobotsLlmsTests(TestCase):
    def _bodies(self, client):
        robots = client.get(reverse('core:robots'))
        llms = client.get(reverse('core:llms'))
        self.assertEqual(robots.status_code, 200)
        self.assertEqual(llms.status_code, 200)
        self.assertIn('text/plain', robots['Content-Type'])
        self.assertIn('text/plain', llms['Content-Type'])
        return robots.content.decode(), llms.content.decode()

    def test_both_modes_hide_admin_path_and_list_sitemap(self):
        with override_settings(ADMIN_URL=f'{_SECRET}/'):
            for enabled in (False, True):
                with self.subTest(enabled=enabled):
                    with forced_exchange_client(enabled) as client:
                        robots, llms = self._bodies(client)
                    self.assertIn('Disallow: /admin/', robots)
                    self.assertIn('Sitemap: https://obmin21.com/sitemap.xml', robots)
                    self.assertNotIn(_SECRET, robots)
                    self.assertNotIn(_SECRET, llms)
                    self.assertNotIn(f'Disallow: /{_SECRET}/', robots)
                    self.assertNotIn('Disallow: /theme.css', robots)
                    self.assertNotIn('Disallow: /static/', robots)
                    for rule in ('/partials/', '/tinymce/', '/htmx/', '/telegram/', '/*?*sort=', '/*?*utm_'):
                        self.assertIn(f'Disallow: {rule}', robots)
                    self.assertFalse(matches_stop_words(robots), robots)
                    self.assertIn('https://obmin21.com/kursy/', llms)
                    if enabled:
                        self.assertFalse(contains_stop_word(llms), llms)
                        self.assertFalse(matches_stop_words(llms), llms)
                    else:
                        self.assertTrue(contains_stop_word(llms))
                        self.assertTrue(matches_stop_words(llms))

    def test_admin_prefix_sends_robots_header(self):
        login = self.client.get('/admin/login/')
        self.assertEqual(login.get('X-Robots-Tag'), 'noindex, nofollow')
        home = self.client.get('/')
        self.assertIsNone(home.get('X-Robots-Tag'))
        with override_settings(ADMIN_URL=f'{_SECRET}/'):
            secret = self.client.get(f'/{_SECRET}/login/')
            self.assertEqual(secret.get('X-Robots-Tag'), 'noindex, nofollow')
            plain = self.client.get('/admin/login/')
            self.assertIsNone(plain.get('X-Robots-Tag'))
            robots = self.client.get('/robots.txt').content.decode()
            self.assertNotIn(_SECRET, robots)
