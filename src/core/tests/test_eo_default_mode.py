"""Без env режиму обмін вимкнений: публічні сторінки відкриті."""

import os
import sys
from contextlib import contextmanager
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import (
    AdvantagesPage,
    BlogPage,
    CitiesPage,
    ContactsPage,
    CookiePage,
    FaqPage,
    HomePage,
    OfferPage,
    PrivacyPage,
    RatesPage,
    ReviewsPage,
    ServicesPage,
)
from src.core.exchange_mode import is_exchange_only
from src.core.models import SiteSettings
from src.rates.models import CurrencyPair

EXCHANGE_ONLY_ENV = 'EXCHANGE_ONLY_MODE'
HIDDEN_STATUS_ENV = 'HIDDEN_PAGE_STATUS'
_ENV_KEYS = (EXCHANGE_ONLY_ENV, HIDDEN_STATUS_ENV)
_CACHE_PREFIXES = (
    'src.core.',
    'src.blog.',
    'src.rates.',
    'src.reviews.',
    'src.network.',
    'src.content.',
    'django.contrib.sitemaps',
)
_PAGE_MODELS = (
    HomePage,
    RatesPage,
    ServicesPage,
    AdvantagesPage,
    FaqPage,
    BlogPage,
    ReviewsPage,
    ContactsPage,
    CitiesPage,
    PrivacyPage,
    OfferPage,
    CookiePage,
)


def clear_exchange_caches():
    """django cache і lru_cache модулів режиму, sitemap і хрома."""
    cache.clear()
    for name, module in list(sys.modules.items()):
        if module is None or not name.startswith(_CACHE_PREFIXES):
            continue
        for obj in list(vars(module).values()):
            owner = getattr(obj, '__module__', '') or ''
            clear = getattr(obj, 'cache_clear', None)
            info = getattr(obj, 'cache_info', None)
            if owner.startswith(_CACHE_PREFIXES) and callable(clear) and callable(info):
                clear()


def _require_forced_mode(enabled, status):
    from src.core.exchange_mode import hidden_page_status

    actual = is_exchange_only()
    if actual != enabled:
        raise AssertionError(
            f'{EXCHANGE_ONLY_ENV}={os.environ.get(EXCHANGE_ONLY_ENV)!r} '
            f'але is_exchange_only()={actual}'
        )
    if status is None:
        return
    actual_status = hidden_page_status()
    if actual_status != status:
        raise AssertionError(
            f'{HIDDEN_STATUS_ENV}={os.environ.get(HIDDEN_STATUS_ENV)!r} '
            f'але hidden_page_status()={actual_status}'
        )


@contextmanager
def forced_exchange_client(enabled, status=None):
    """Примусовий режим через env. Новий Client після скидання кешів."""
    env = {EXCHANGE_ONLY_ENV: '1' if enabled else '0'}
    if status is not None:
        status = int(status)
        env[HIDDEN_STATUS_ENV] = str(status)
    with patch.dict(os.environ, env):
        clear_exchange_caches()
        client = Client()
        try:
            _require_forced_mode(bool(enabled), status)
            yield client
        finally:
            clear_exchange_caches()


class DefaultExchangeModeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.settings_row = SiteSettings.objects.create()
        for model in _PAGE_MODELS:
            model.load()
        cls.pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-uah',
        )
        cls.category = Category.objects.create(name='Поради', slug='porady')
        cls.post = Post.objects.create(
            category=cls.category,
            title='Курс долара',
            slug='kurs-dolara',
            body='Текст про долар',
            status=Post.Status.PUBLISHED,
        )

    def setUp(self):
        super().setUp()
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        self._clear_mode_env()

    def tearDown(self):
        self._clear_mode_env()
        for key, value in self._saved_env.items():
            if value is not None:
                os.environ[key] = value
        super().tearDown()

    def _clear_mode_env(self):
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        clear_exchange_caches()

    def test_mode_is_off_and_pages_are_open(self):
        self.assertFalse(SiteSettings._meta.get_field('exchange_only').default)
        self.settings_row.refresh_from_db()
        self.assertFalse(self.settings_row.exchange_only)
        self.assertIsNone(os.environ.get(EXCHANGE_ONLY_ENV))
        self.assertIsNone(os.environ.get(HIDDEN_STATUS_ENV))
        self.assertFalse(is_exchange_only())
        for url in self._public_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def _public_urls(self):
        return (
            reverse('core:home'),
            reverse('rates:rates_page'),
            reverse('content:services'),
            reverse('content:advantages'),
            reverse('content:faq'),
            reverse('blog:post_list'),
            reverse('reviews:review_list'),
            reverse('content:contacts'),
            reverse('network:city_list'),
            reverse('content:privacy'),
            reverse('content:offer'),
            reverse('content:cookies'),
            reverse('core:sitemap'),
            reverse('core:robots'),
            reverse('rates:pair_detail', kwargs={'slug': self.pair.slug}),
            reverse('blog:post_detail', kwargs={'slug': self.post.slug}),
            reverse('blog:category', kwargs={'category_slug': self.category.slug}),
        )
