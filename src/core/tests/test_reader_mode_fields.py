import importlib
import os
from pathlib import Path

from django.apps import apps
from django.contrib import admin
from django.core.cache import cache
from django.test import TestCase

import src.content.admin  # noqa: F401
import src.network.admin  # noqa: F401
from src.blog.models import Category, Post
from src.content.admin_items import HomeStatAdmin
from src.content.models import CitiesPage, HomePage, HomeStat, ReviewsPage, Service
from src.content.reader_mode_copy import (
    CITIES_PAGE_MODE_COPY,
    REVIEWS_PAGE_MODE_COPY,
    exchange_plain,
    fill_reader_mode_fields,
    stat_base_is_clean,
)
from src.core.exchange_fields import MODE_FIELD_HELP
from src.core.exchange_mode import mode_text
from src.core.exchange_stopwords import matches_stop_words
from src.core.models import SiteSettings
from src.core.tests.test_services_page_mode import load_filter_stopwords
from src.network.admin import CityAdmin, ContactCityAdmin, MapCityAdmin
from src.network.city_mode_copy import fill_city_name_mode
from src.network.models import City

_ENV = 'EXCHANGE_ONLY_MODE'
_ROOT = Path(__file__).resolve().parents[3]
_LAYOUT_MODE_NAMES = (
    'h1a_mode',
    'h1b_mode',
    'lead_mode',
    'read_mode',
    'fig_cap_mode',
    'fig_url_mode',
    'plain_mode',
    'h_mode',
    'fig_mode',
)
_POST_MODE = (
    'title_mode',
    'excerpt_mode',
    'seo_title_mode',
    'seo_description_mode',
)
_SERVICE_BLOCK_MODE = (
    'block_text_mode',
    'block_points_mode',
    'block_cta_mode',
)


def _seed_stats():
    module = importlib.import_module(
        'src.content.migrations.0010_seed_home_section_links',
    )
    return module.STATS


def _follows(fields, base):
    names = list(fields)
    return names[names.index(base) + 1] == f'{base}_mode'


class ReaderModeFieldTests(TestCase):
    def setUp(self):
        self._saved_env = os.environ.get(_ENV)
        os.environ.pop(_ENV, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)
        cache.clear()

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = self._saved_env
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def test_new_fields_sit_beside_bases_and_fail_closed(self):
        pairs = (
            (HomeStat, 'number', 'number_mode'),
            (HomeStat, 'text', 'text_mode'),
            (City, 'name', 'name_mode'),
            (CitiesPage, 'title', 'title_mode'),
            (CitiesPage, 'intro', 'intro_mode'),
            (ReviewsPage, 'title', 'title_mode'),
            (ReviewsPage, 'seo_title', 'seo_title_mode'),
            (ReviewsPage, 'seo_description', 'seo_description_mode'),
        )
        for model, base_name, mode_name in pairs:
            base = model._meta.get_field(base_name)
            mode = model._meta.get_field(mode_name)
            self.assertTrue(mode.blank)
            self.assertEqual(mode.help_text, MODE_FIELD_HELP)
            if base.get_internal_type() == 'CharField':
                self.assertEqual(mode.max_length, base.max_length)
                self.assertEqual(mode.get_internal_type(), 'CharField')
            else:
                self.assertEqual(mode.get_internal_type(), 'TextField')

        self.assertTrue(_follows(HomeStatAdmin.fields, 'number'))
        self.assertTrue(_follows(HomeStatAdmin.fields, 'text'))
        self.assertTrue(_follows(CityAdmin.fields, 'name'))
        for admin_cls, title in (
            (MapCityAdmin, 'Місто'),
            (ContactCityAdmin, 'Контакти міста'),
        ):
            fields = dict(admin_cls.fieldsets)[title]['fields']
            self.assertTrue(_follows(fields, 'name'))

        cities_admin = admin.site._registry[CitiesPage]
        self.assertTrue(_follows(cities_admin.content_fields, 'title'))
        self.assertTrue(_follows(cities_admin.content_fields, 'intro'))
        reviews_admin = admin.site._registry[ReviewsPage]
        review_fields = reviews_admin.content_fieldsets[0][1]['fields']
        self.assertTrue(_follows(review_fields, 'title'))
        self.assertTrue(_follows(review_fields, 'seo_title'))
        self.assertTrue(_follows(review_fields, 'seo_description'))

        post_names = {field.name for field in Post._meta.fields}
        for name in _POST_MODE:
            self.assertIn(name, post_names)
        for name in _LAYOUT_MODE_NAMES:
            self.assertNotIn(name, post_names)
        service_names = {field.name for field in Service._meta.fields}
        for name in _SERVICE_BLOCK_MODE:
            self.assertIn(name, service_names)
        city_names = {field.name for field in City._meta.fields}
        self.assertIn('banner_suffix_mode', city_names)
        self.assertIn('banner_button_mode', city_names)

    def test_fill_is_idempotent_skips_stopwords_and_keeps_edits(self):
        _words, filter_matches = load_filter_stopwords()
        page = HomePage.objects.get(pk=1)
        dirty = HomeStat.objects.create(
            page=page,
            number='1',
            text='Обмін криптовалюти та перекази золота',
            sort_order=20,
        )
        kept = HomeStat.objects.create(
            page=page,
            number='100%',
            text='Прозорі умови обміну готівки',
            number_mode='Своя цифра',
            text_mode='Свій текст картки',
            sort_order=21,
            exchange_safe=True,
        )
        fresh = HomeStat.objects.create(
            page=page,
            number='  15  ',
            text='<p><b>Відділень</b> — обмін готівкової валюти</p>',
            number_mode='   ',
            text_mode='',
            sort_order=22,
        )
        city = City.objects.create(name='Чернігів', slug='chernihiv-reader-mode')
        city.name_mode = 'Своя назва'
        city.save(update_fields=['name_mode'])
        other = City.objects.create(name='  Полтава  ', slug='poltava-reader-mode')
        category = Category.objects.create(name='Поради', slug='porady-reader-mode')
        post = Post.objects.create(
            category=category,
            title='Курс долара',
            slug='kurs-dolara-reader-mode',
            body='Текст',
            excerpt='Анонс',
            seo_title='SEO',
            seo_description='Опис',
        )
        service = Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut-reader-mode',
            short_desc='Готівка',
            block_text='',
            block_points='',
            block_cta='',
        )
        for model, mapping in (
            (CitiesPage, CITIES_PAGE_MODE_COPY),
            (ReviewsPage, REVIEWS_PAGE_MODE_COPY),
        ):
            row = model.objects.get(pk=1)
            model.objects.filter(pk=row.pk).update(**{name: '' for name in mapping})

        fill_reader_mode_fields(apps, None)
        fill_reader_mode_fields(apps, None)
        fill_city_name_mode(apps, None)
        fill_city_name_mode(apps, None)

        dirty.refresh_from_db()
        kept.refresh_from_db()
        fresh.refresh_from_db()
        city.refresh_from_db()
        other.refresh_from_db()
        post.refresh_from_db()
        service.refresh_from_db()
        cities = CitiesPage.objects.get(pk=1)
        reviews = ReviewsPage.objects.get(pk=1)

        self.assertEqual(dirty.number_mode, '')
        self.assertEqual(dirty.text_mode, '')
        self.assertFalse(dirty.exchange_safe)
        self.assertTrue(kept.exchange_safe)
        self.assertEqual(kept.number_mode, 'Своя цифра')
        self.assertEqual(kept.text_mode, 'Свій текст картки')
        self.assertEqual(fresh.number_mode, '15')
        self.assertEqual(fresh.text_mode, 'Відділень — обмін готівкової валюти')
        self.assertFalse(fresh.exchange_safe)
        self.assertEqual(city.name_mode, 'Своя назва')
        self.assertEqual(other.name_mode, 'Полтава')
        for name in _POST_MODE:
            self.assertEqual(getattr(post, name), '')
        for name in _SERVICE_BLOCK_MODE:
            self.assertEqual(getattr(service, name), '')
        for name, text in CITIES_PAGE_MODE_COPY.items():
            self.assertEqual(getattr(cities, name), text)
        for name, text in REVIEWS_PAGE_MODE_COPY.items():
            self.assertEqual(getattr(reviews, name), text)

        cities.title_mode = 'Свій заголовок міст'
        cities.save(update_fields=['title_mode'])
        fill_reader_mode_fields(apps, None)
        cities.refresh_from_db()
        self.assertEqual(cities.title_mode, 'Свій заголовок міст')
        self.assertEqual(cities.intro_mode, CITIES_PAGE_MODE_COPY['intro_mode'])

        filled = []
        for order, number, text in _seed_stats():
            row = HomeStat.objects.get(page=page, sort_order=order, number=number)
            self.assertEqual(stat_base_is_clean(number, text), not matches_stop_words(number, text))
            if matches_stop_words(number, text):
                self.assertEqual(row.number_mode, '')
                self.assertEqual(row.text_mode, '')
                self.assertIn('крипт', text.casefold())
            else:
                self.assertEqual(row.number_mode, exchange_plain(number))
                self.assertEqual(row.text_mode, exchange_plain(text))
                filled.append(row.number_mode)
                filled.append(row.text_mode)
            self.assertFalse(row.exchange_safe)
        filled.extend(CITIES_PAGE_MODE_COPY.values())
        filled.extend(REVIEWS_PAGE_MODE_COPY.values())
        filled.append(fresh.number_mode)
        filled.append(fresh.text_mode)
        filled.append(other.name_mode)
        self.assertTrue(filled)
        for text in filled:
            self.assertFalse(matches_stop_words(text), text)
            self.assertFalse(filter_matches(text), text)
        self.assertEqual(
            [text for text in filled if matches_stop_words(text) or filter_matches(text)],
            [],
        )

    def test_empty_mode_is_hidden(self):
        page = HomePage.objects.get(pk=1)
        stat = HomeStat.objects.create(
            page=page,
            number='20+',
            text='Відділення обміну',
            number_mode='',
            text_mode='   ',
            sort_order=30,
        )
        cities = CitiesPage.objects.get(pk=1)
        cities.title_mode = ''
        cities.save(update_fields=['title_mode'])
        self._mode(True)
        self.assertEqual(mode_text(stat, 'number'), '')
        self.assertEqual(mode_text(stat, 'text'), '')
        self.assertEqual(mode_text(cities, 'title'), '')
        stat.text_mode = '  Готівковий обмін  '
        stat.save(update_fields=['text_mode'])
        self.assertEqual(mode_text(stat, 'text'), 'Готівковий обмін')
        self.assertFalse(stat.exchange_safe)
        self._mode(False)
        self.assertEqual(mode_text(stat, 'number'), '20+')
        self.assertEqual(mode_text(stat, 'text'), 'Відділення обміну')

    def test_migrations_and_seed_call_fill_without_exchange_safe(self):
        content = (
            _ROOT / 'src/content/migrations/0027_reader_mode_fields.py'
        ).read_text(encoding='utf-8')
        network = (
            _ROOT / 'src/network/migrations/0007_city_name_mode.py'
        ).read_text(encoding='utf-8')
        seed = (
            _ROOT / 'src/core/management/commands/seed_demo.py'
        ).read_text(encoding='utf-8')
        self.assertIn('fill_reader_mode_fields', content)
        self.assertIn('noop_reverse', content)
        self.assertIn('number_mode', content)
        self.assertIn('text_mode', content)
        self.assertIn('fill_city_name_mode', network)
        self.assertIn('noop_reverse', network)
        self.assertIn('name_mode', network)
        for source in (content, network):
            self.assertNotIn('exchange_safe', source)
        self.assertIn('fill_reader_mode_fields(apps, None)', seed)
        self.assertIn('fill_city_name_mode(apps, None)', seed)
        self.assertNotIn('exchange_safe', seed)
