import os

from django.core.cache import cache
from django.test import TestCase

from src.blog.models import Category, Post
from src.content.models import Service
from src.core.models import SiteSettings
from src.core.sitemaps import (
    CategorySitemap,
    PairSitemap,
    PostSitemap,
    ServiceSitemap,
    public_services,
)
from src.rates.models import CurrencyPair

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class SitemapExchangeTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self.advice = Category.objects.create(name='Поради', slug='porady')
        self.archive = Category.objects.create(name='Архів', slug='arkhiv')
        self.empty = Category.objects.create(name='Порожня', slug='porozhnya')
        Post.objects.create(
            category=self.advice,
            title='Курс долара',
            slug='kurs-dolara',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        Post.objects.create(
            category=self.archive,
            title='Окрема нотатка',
            slug='okrema-notatka',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        Post.objects.create(
            category=self.advice,
            title='Чернетка',
            slug='chernetka',
            body='Текст',
            status=Post.Status.DRAFT,
            exchange_safe=True,
        )
        CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
            exchange_safe=True,
        )
        CurrencyPair.objects.create(
            code='EUR',
            name='Євро',
            slug='eur-uah',
            exchange_safe=False,
        )
        CurrencyPair.objects.create(
            code='BTC/USDT',
            name='Bitcoin',
            slug='btc-usdt',
            exchange_safe=False,
        )
        Service.objects.create(
            title='Обмін валют',
            slug='hotivka',
            short_desc='Готівка',
            is_active=True,
            exchange_safe=True,
        )
        Service.objects.create(
            title='Прихована послуга',
            slug='pryhovana',
            short_desc='Текст',
            is_active=True,
            exchange_safe=False,
        )
        Service.objects.create(
            title='SWIFT переказ',
            slug='swift-perekaz',
            short_desc='За кордон',
            is_active=True,
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

    def _xml(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_mode_off_lists_published_posts_pairs_and_categories(self):
        self._mode(False)
        xml = self._xml()
        self.assertIn('/blog/kurs-dolara/', xml)
        self.assertIn('/blog/okrema-notatka/', xml)
        self.assertNotIn('chernetka', xml)
        self.assertIn('/usd-uah/', xml)
        self.assertIn('/eur-uah/', xml)
        self.assertIn('/btc-usdt/', xml)
        self.assertIn('/blog/kategoriya/porady/', xml)
        self.assertIn('/blog/kategoriya/arkhiv/', xml)
        self.assertNotIn('/blog/kategoriya/porozhnya/', xml)
        self.assertNotIn('hotivka', xml)
        self.assertNotIn('swift-perekaz', xml)
        self.assertEqual(
            set(PostSitemap().items().values_list('slug', flat=True)),
            {'kurs-dolara', 'okrema-notatka'},
        )

    def test_mode_on_drops_hidden_posts_pairs_and_categories(self):
        self._mode(True)
        xml = self._xml()
        self.assertIn('/blog/kurs-dolara/', xml)
        self.assertNotIn('okrema-notatka', xml)
        self.assertNotIn('chernetka', xml)
        self.assertIn('/usd-uah/', xml)
        self.assertNotIn('eur-uah', xml)
        self.assertNotIn('btc-usdt', xml)
        self.assertIn('/blog/kategoriya/porady/', xml)
        self.assertNotIn('/blog/kategoriya/arkhiv/', xml)
        self.assertNotIn('/blog/kategoriya/porozhnya/', xml)
        self.assertNotIn('hotivka', xml)
        self.assertNotIn('pryhovana', xml)
        self.assertNotIn('swift-perekaz', xml)
        self.assertEqual(
            list(PairSitemap().items().values_list('slug', flat=True)),
            ['usd-uah'],
        )
        self.assertEqual(
            list(CategorySitemap().items().values_list('slug', flat=True)),
            ['porady'],
        )
        self.assertEqual(ServiceSitemap().items(), [])

    def test_public_services_follow_visible_and_topic(self):
        self._mode(False)
        self.assertEqual(
            list(public_services().values_list('slug', flat=True)),
            ['hotivka', 'pryhovana', 'swift-perekaz'],
        )
        self._mode(True)
        self.assertEqual(
            list(public_services().values_list('slug', flat=True)),
            ['hotivka'],
        )
