import os
import re
from html import unescape

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import RatesPage, ServicesPage
from src.core.models import SiteSettings
from src.core.seo_public import clean_public_url, sanitize_public_html, sanitize_response
from src.core.seo_words import contains_stop_word, strip_stop_words

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class StopWordTests(SimpleTestCase):
    def test_uk_and_ru_forms_are_removed(self):
        samples = {
            'криптовалюта': '',
            'крипта': '',
            'crypto': '',
            'cryptocurrency desk': 'desk',
            'Курс BTC/USDT на сьогодні': 'Курс на сьогодні',
            'SWIFT-переказ': '',
            'перекази по Україні': 'по Україні',
            'переказів': '',
            'перевод денег': 'денег',
            'переводов': '',
            'золото': '',
            'золотого': '',
            'золотые слитки': 'слитки',
            'Інвестиційне золото: як купити': 'Інвестиційне: як купити',
            'зношені купюри': 'купюри',
            'зношених': '',
            'изношенные купюры': 'купюры',
            'оптовий курс': 'курс',
            'оптом': '',
            'опт': '',
            'оптовый': '',
            'оптимальний варіант': 'оптимальний варіант',
            'оптимізація': 'оптимізація',
            'оптика': 'оптика',
        }
        for raw, expected in samples.items():
            self.assertEqual(strip_stop_words(raw), expected, raw)
            if expected == raw:
                self.assertFalse(contains_stop_word(raw), raw)
            else:
                self.assertTrue(contains_stop_word(raw), raw)


def _seo_bits(html):
    chunks = re.findall(r'<title>(.*?)</title>', html, re.S)
    chunks.extend(re.findall(
        r'<meta\b[^>]*(?:name|property)=["\'](?:description|og:[^"\']+)["\'][^>]*>',
        html,
        re.I,
    ))
    chunks.extend(re.findall(
        r'<link\b[^>]*rel=["\'](?:canonical|alternate)["\'][^>]*>',
        html,
        re.I,
    ))
    chunks.extend(re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
        html,
        re.I | re.S,
    ))
    return unescape('\n'.join(chunks))


class PublicSeoTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self.category = Category.objects.create(name='Поради', slug='porady')
        Post.objects.create(
            category=self.category,
            title='Окрема нотатка',
            slug='okrema-notatka',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        self.article = Post.objects.create(
            category=self.category,
            title='Інвестиційне золото: як купити',
            slug='investytsiine-zlytok',
            excerpt='Як зберегти заощадження',
            body='Текст про збереження.',
            seo_description='Як інвестувати в золото та зберегти кошти',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        Post.objects.create(
            category=self.category,
            title='Курс долара',
            slug='kurs-dolara',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)

    def test_open_pages_lose_stop_words_in_seo(self):
        self._mode(True)
        rates = RatesPage.load()
        rates.seo_title = 'Курси криптовалюти BTC та SWIFT'
        rates.seo_description = 'Актуальний курс долара без комісії'
        rates.save()
        rates_html = self.client.get(reverse('rates:rates_page')).content.decode()
        bits = _seo_bits(rates_html)
        self.assertIn('Курси та', bits)
        self.assertFalse(contains_stop_word(bits))

        services = self.client.get(reverse('content:services'))
        self.assertEqual(services.status_code, 200)
        self.assertFalse(contains_stop_word(_seo_bits(services.content.decode())))

        article = self.client.get(
            reverse('blog:post_detail', args=[self.article.slug]),
        )
        self.assertEqual(article.status_code, 200)
        article_bits = _seo_bits(article.content.decode())
        self.assertIn('Інвестиційне: як купити', article_bits)
        self.assertIn('Як інвестувати в та зберегти кошти', article_bits)
        self.assertNotIn('okrema-notatka', article_bits)
        self.assertFalse(contains_stop_word(article_bits))
        self.assertNotIn('FAQPage', article_bits)

        faq = self.client.get(reverse('content:faq'))
        self.assertEqual(faq.status_code, 200)
        self.assertNotIn('FAQPage', faq.content.decode())

    def test_canonical_query_drops_crypto_board(self):
        self._mode(True)
        response = self.client.get(reverse('rates:rates_page') + '?board=crypto')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        href = re.search(r'rel="canonical" href="([^"]+)"', html).group(1)
        self.assertNotIn('crypto', href.lower())
        self.assertNotIn('board=', href)
        self.assertTrue(href.endswith('/kursy/'))

    def test_mode_off_keeps_source_seo_text(self):
        self._mode(False)
        page = ServicesPage.load()
        page.seo_title = 'Послуги: криптовалюта і золото'
        page.seo_description = 'Перекази SWIFT'
        page.save()
        html = self.client.get(reverse('content:services')).content.decode()
        self.assertIn('криптовалюта', html)
        self.assertIn('Перекази SWIFT', html)

    def test_admin_html_is_left_alone(self):
        self._mode(True)
        request = RequestFactory().get('/admin/')
        response = HttpResponse('<title>BTC SWIFT</title>', content_type='text/html')
        cleaned = sanitize_response(request, response)
        self.assertIn('BTC SWIFT', cleaned.content.decode())

    def test_markup_drops_hidden_links_and_stop_words(self):
        self._mode(True)
        html = (
            '<title>Курси криптовалюти BTC</title>'
            '<meta name="description" content="SWIFT і золото">'
            '<meta property="og:title" content="Оптовий переказ">'
            '<meta property="og:url" content="https://testserver/btc-usdt/">'
            '<link rel="canonical" href="https://testserver/kursy/?board=crypto">'
            '<link rel="alternate" hreflang="ru" '
            'href="https://testserver/blog/okrema-notatka/">'
            '<script type="application/ld+json">'
            '{"@type":"ItemList","name":"Криптовалюта","itemListElement":['
            '{"url":"https://testserver/blog/okrema-notatka/"},'
            '{"url":"/blog/kurs-dolara/"}]}'
            '</script>'
        )
        request = RequestFactory().get('/kursy/')
        cleaned = sanitize_public_html(html, request)
        self.assertIn('<title>Курси</title>', cleaned)
        self.assertNotIn('name="description"', cleaned)
        self.assertNotIn('og:title', cleaned)
        self.assertNotIn('og:url', cleaned)
        self.assertIn('href="https://testserver/kursy/"', cleaned)
        self.assertNotIn('hreflang', cleaned)
        self.assertNotIn('okrema-notatka', cleaned)
        self.assertIn('/blog/kurs-dolara/', cleaned)
        self.assertNotIn('FAQPage', cleaned)
        self.assertFalse(contains_stop_word(_seo_bits(cleaned)))

    def test_clean_public_url_removes_hidden_path(self):
        self._mode(True)
        request = RequestFactory().get('/')
        self.assertEqual(
            clean_public_url('https://testserver/blog/okrema-notatka/', request),
            '',
        )
        self.assertEqual(
            clean_public_url('/blog/kurs-dolara/', request),
            '/blog/kurs-dolara/',
        )
