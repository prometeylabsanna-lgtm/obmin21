import os
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import (
    AdvantageItem,
    FaqItem,
    HomePage,
    HomeStat,
    Service,
)
from src.core.exchange_mode import (
    exchange_only,
    hidden_page_status,
    is_mode_forced_by_env,
)
from src.core.models import SiteSettings
from src.rates.models import CurrencyPair
from src.reviews.models import Review

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class ExchangeModeTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        self.settings_row = SiteSettings.load()

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _set_mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)

    def test_reads_settings_without_memory_cache(self):
        self._set_mode(False)
        self.assertFalse(exchange_only())
        self._set_mode(True)
        self.assertTrue(exchange_only())
        self.assertFalse(SiteSettings.load().exchange_only)

    def test_env_overrides_settings(self):
        self._set_mode(False)
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': '1'}):
            self.assertTrue(is_mode_forced_by_env())
            self.assertTrue(exchange_only())
        self._set_mode(True)
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': '0'}):
            self.assertTrue(is_mode_forced_by_env())
            self.assertFalse(exchange_only())
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': ' 1 '}):
            self.assertTrue(exchange_only())
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': 'yes'}):
            self.assertFalse(is_mode_forced_by_env())
            self.assertTrue(exchange_only())

    def test_request_cache_does_not_leak_to_next_call(self):
        self._set_mode(False)
        request = RequestFactory().get('/')
        self.assertFalse(exchange_only(request))
        self._set_mode(True)
        self.assertFalse(exchange_only(request))
        self.assertTrue(exchange_only())
        self.assertTrue(exchange_only(RequestFactory().get('/')))

    def test_hidden_page_status_env_overrides_settings(self):
        self.assertEqual(hidden_page_status(), 503)
        SiteSettings.objects.filter(pk=1).update(hidden_page_status=404)
        self.assertEqual(hidden_page_status(), 404)
        with patch.dict(os.environ, {'HIDDEN_PAGE_STATUS': '503'}):
            self.assertEqual(hidden_page_status(), 503)
        with patch.dict(os.environ, {'HIDDEN_PAGE_STATUS': '404'}):
            self.assertEqual(hidden_page_status(), 404)
        with patch.dict(os.environ, {'HIDDEN_PAGE_STATUS': '410'}):
            self.assertEqual(hidden_page_status(), 404)

    def test_visible_filters_only_in_mode(self):
        Service.objects.create(
            title='Безпечна',
            slug='bezpechna',
            short_desc='Обмін',
            exchange_safe=True,
        )
        Service.objects.create(
            title='Прихована',
            slug='pryhovana',
            short_desc='Обмін',
            exchange_safe=False,
        )
        self._set_mode(False)
        self.assertEqual(Service.objects.visible().count(), 2)
        self._set_mode(True)
        self.assertEqual(
            list(Service.objects.visible().values_list('slug', flat=True)),
            ['bezpechna'],
        )
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': '0'}):
            self.assertEqual(Service.objects.visible().count(), 2)

    def test_new_records_of_seven_models_start_unchecked(self):
        page = HomePage.load()
        category = Category.objects.create(name='Новини', slug='novyny-mode')
        records = [
            Service.objects.create(title='Послуга', slug='posluha-mode', short_desc='Текст'),
            CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-mode'),
            Review.objects.create(name='Олена', text='Добре'),
            Post.objects.create(
                category=category,
                title='Стаття',
                slug='stattia-mode',
                body='Текст',
            ),
            FaqItem.objects.create(question='Питання', answer='Відповідь'),
            AdvantageItem.objects.create(
                audience=AdvantageItem.Audience.CITIZENS,
                text='Пункт',
            ),
            HomeStat.objects.create(page=page, number='7K', text='Клієнти'),
        ]
        self._set_mode(False)
        for record in records:
            self.assertFalse(record.exchange_safe)
            visible_ids = set(type(record).objects.visible().values_list('pk', flat=True))
            self.assertIn(record.pk, visible_ids)
        self._set_mode(True)
        for record in records:
            visible_ids = set(type(record).objects.visible().values_list('pk', flat=True))
            self.assertNotIn(record.pk, visible_ids)

    def test_data_migration_inverts_saved_flag(self):
        import importlib

        migration = importlib.import_module(
            'src.core.migrations.0007_sitesettings_exchange_only',
        )
        invert_exchange_only = migration.invert_exchange_only

        class _Apps:
            def get_model(self, app_label, model_name):
                if (app_label, model_name) != ('core', 'SiteSettings'):
                    raise AssertionError(app_label, model_name)
                return SiteSettings

        self.settings_row.exchange_only = False
        self.settings_row.save(update_fields=['exchange_only'])
        invert_exchange_only(_Apps(), None)
        self.settings_row.refresh_from_db()
        self.assertTrue(self.settings_row.exchange_only)
        invert_exchange_only(_Apps(), None)
        self.settings_row.refresh_from_db()
        self.assertFalse(self.settings_row.exchange_only)

    def test_public_services_ignore_checkbox_for_now(self):
        Service.objects.create(
            title='Готівковий обмін',
            slug='hotivkovyi-mode',
            short_desc='Обмін долара у відділенні',
            is_active=True,
        )
        self._set_mode(True)
        response = self.client.get(reverse('content:services'))
        self.assertContains(response, 'Готівковий обмін')
