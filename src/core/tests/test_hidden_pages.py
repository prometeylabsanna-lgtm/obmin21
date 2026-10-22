import os
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.urls.resolvers import ResolverMatch

from src.blog.models import Category, Post
from src.content.models import Service
from src.core.hidden_response import is_hidden_match, service_public_path
from src.core.models import SiteSettings
from src.rates.models import CurrencyPair

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


def _service_match(slug, url_name='service_detail'):
    return ResolverMatch(
        lambda request, slug: None,
        (),
        {'slug': slug},
        url_name=url_name,
        app_names=['content'],
        namespaces=['content'],
        route='posluhy/<slug:slug>/',
    )


class HiddenPageTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self.category = Category.objects.create(name='Поради', slug='porady')
        self.empty_category = Category.objects.create(name='Порожня', slug='porozhnya')
        self.quiet_category = Category.objects.create(name='Архів', slug='arkhiv')
        self.safe_post = Post.objects.create(
            category=self.category,
            title='Курс долара',
            slug='kurs-dolara',
            body='Текст про долар',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        self.hidden_post = Post.objects.create(
            category=self.quiet_category,
            title='Окрема нотатка',
            slug='okrema-notatka',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        self.draft = Post.objects.create(
            category=self.category,
            title='Чернетка',
            slug='chernetka',
            body='Текст',
            status=Post.Status.DRAFT,
            exchange_safe=False,
        )
        self.safe_pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
            exchange_safe=True,
        )
        self.unsafe_pair = CurrencyPair.objects.create(
            code='EUR',
            name='Євро',
            slug='eur-uah',
            exchange_safe=False,
        )
        self.crypto_pair = CurrencyPair.objects.create(
            code='BTC/USDT',
            name='Bitcoin',
            slug='btc-usdt',
            exchange_safe=True,
        )
        self.inactive_pair = CurrencyPair.objects.create(
            code='GBP',
            name='Фунт',
            slug='gbp-uah',
            is_active=False,
            exchange_safe=False,
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

    def test_mode_off_keeps_pages_open(self):
        self._mode(False)
        response = self.client.get(
            reverse('blog:post_detail', args=[self.hidden_post.slug]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Цей матеріал тимчасово недоступний')

    def test_unsafe_post_returns_503_page(self):
        self._mode(True)
        response = self.client.get(
            reverse('blog:post_detail', args=[self.hidden_post.slug]),
        )
        self.assertContains(
            response,
            'Цей матеріал тимчасово недоступний',
            status_code=503,
        )
        self.assertContains(response, 'href="/kursy/"', status_code=503)
        self.assertContains(response, 'На головну', status_code=503)
        self.assertEqual(response['Retry-After'], '86400')
        self.assertContains(response, 'hidden-page.css', status_code=503)

    def test_safe_post_stays_open(self):
        self._mode(True)
        response = self.client.get(
            reverse('blog:post_detail', args=[self.safe_post.slug]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Цей матеріал тимчасово недоступний')

    def test_draft_stays_not_found(self):
        self._mode(True)
        response = self.client.get(
            reverse('blog:post_detail', args=[self.draft.slug]),
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(
            response,
            'Цей матеріал тимчасово недоступний',
            status_code=404,
        )

    def test_empty_category_is_hidden_and_live_category_is_open(self):
        self._mode(True)
        hidden = self.client.get(
            reverse('blog:category', args=[self.empty_category.slug]),
        )
        quiet = self.client.get(
            reverse('blog:category', args=[self.quiet_category.slug]),
        )
        opened = self.client.get(
            reverse('blog:category', args=[self.category.slug]),
        )
        self.assertEqual(hidden.status_code, 503)
        self.assertEqual(quiet.status_code, 503)
        self.assertEqual(opened.status_code, 200)

    def test_missing_category_is_not_found(self):
        self._mode(True)
        response = self.client.get(reverse('blog:category', args=['nema-takoi']))
        self.assertEqual(response.status_code, 404)

    def test_pairs_follow_visible(self):
        self._mode(True)
        safe = self.client.get(
            reverse('rates:pair_detail', args=[self.safe_pair.slug]),
        )
        unsafe = self.client.get(
            reverse('rates:pair_detail', args=[self.unsafe_pair.slug]),
        )
        marked_safe = self.client.get(
            reverse('rates:pair_detail', args=[self.crypto_pair.slug]),
        )
        inactive = self.client.get(
            reverse('rates:pair_detail', args=[self.inactive_pair.slug]),
        )
        self.assertEqual(safe.status_code, 200)
        self.assertEqual(unsafe.status_code, 503)
        self.assertEqual(marked_safe.status_code, 200)
        self.assertEqual(inactive.status_code, 404)

    def test_status_404_omits_retry_after(self):
        self._mode(True)
        SiteSettings.objects.filter(pk=1).update(hidden_page_status=404)
        response = self.client.get(
            reverse('blog:post_detail', args=[self.hidden_post.slug]),
        )
        self.assertContains(
            response,
            'Цей матеріал тимчасово недоступний',
            status_code=404,
        )
        self.assertNotIn('Retry-After', response)

    def test_retry_after_comes_from_settings(self):
        self._mode(True)
        SiteSettings.objects.filter(pk=1).update(retry_after_seconds=3600)
        response = self.client.get(
            reverse('rates:pair_detail', args=[self.unsafe_pair.slug]),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '3600')

    def test_env_overrides_mode_and_status(self):
        self._mode(False)
        path = reverse('blog:post_detail', args=[self.hidden_post.slug])
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': '1'}):
            forced = self.client.get(path)
        self.assertEqual(forced.status_code, 503)
        self._mode(True)
        with patch.dict(os.environ, {
            'EXCHANGE_ONLY_MODE': '0',
            'HIDDEN_PAGE_STATUS': '404',
        }):
            opened = self.client.get(path)
        self.assertEqual(opened.status_code, 200)
        with patch.dict(os.environ, {
            'EXCHANGE_ONLY_MODE': '1',
            'HIDDEN_PAGE_STATUS': '404',
        }):
            missing = self.client.get(path)
        self.assertEqual(missing.status_code, 404)
        self.assertNotIn('Retry-After', missing)

    def test_head_uses_same_status(self):
        self._mode(True)
        response = self.client.head(
            reverse('blog:post_detail', args=[self.hidden_post.slug]),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '86400')

    def test_unknown_service_url_is_not_invented(self):
        self._mode(True)
        Service.objects.create(
            title='SWIFT',
            slug='swift',
            short_desc='Переказ',
            is_active=True,
            exchange_safe=False,
        )
        response = self.client.get('/posluhy/swift/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(service_public_path('swift'), '')

    def test_service_detail_match_uses_exchange_safe_and_topic(self):
        self._mode(True)
        hidden = Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut',
            short_desc='Готівка',
            is_active=True,
            exchange_safe=False,
        )
        swift = Service.objects.create(
            title='SWIFT переказ',
            slug='swift-perekaz',
            short_desc='За кордон',
            seo_title='Міжнародний SWIFT',
            is_active=True,
            exchange_safe=True,
        )
        opened = Service.objects.create(
            title='Обмін валют',
            slug='hotivka',
            short_desc='Готівка',
            is_active=True,
            exchange_safe=True,
        )
        self.assertTrue(is_hidden_match(_service_match(hidden.slug)))
        self.assertTrue(is_hidden_match(_service_match(swift.slug, url_name='custom')))
        self.assertFalse(is_hidden_match(_service_match(opened.slug)))
        self.assertFalse(is_hidden_match(_service_match('nema-posluhy')))
