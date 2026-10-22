import os
import re
import unittest
from pathlib import Path

from django.apps import apps
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.home_copy import SERVICES_MENTION_LEAD
from src.content.models import HomePage, ServicesPage
from src.content.stage3_fill import (
    HOME_SEO_MODE_COPY,
    fill_articles_lead,
    fill_home_seo_mode,
)
from src.core.exchange_fields import MODE_FIELD_HELP, resolved_text
from src.core.exchange_mode import mode_text
from src.core.models import SiteSettings
from src.core.tests.test_services_page_mode import load_filter_stopwords
from src.network.city_mode_copy import CITY_MODE_COPY, fill_city_banner_seo_mode
from src.network.models import Branch, City
from src.reviews.models import Review

_ENV = 'EXCHANGE_ONLY_MODE'
_ROOT = Path(__file__).resolve().parents[3]
_POSLUHY_LEAD = (
    'Окрім обміну валют у мережі Обмін21 доступні грошові перекази по Україні, '
    'міжнародні перекази та обмін електронних валют — умови та підготовка до візиту нижче.'
)
_TEXT_TYPES = frozenset({'CharField', 'TextField'})


class CityBranchHomeSeoModeTests(TestCase):
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

    def test_city_banner_and_seo_text_fields_have_mode(self):
        names = {field.name for field in City._meta.fields}
        missing = []
        for field in City._meta.fields:
            name = field.name
            if field.get_internal_type() not in _TEXT_TYPES:
                continue
            if name.endswith('_mode'):
                continue
            if not (name.startswith('banner_') or name.startswith('seo_')):
                continue
            mode_name = f'{name}_mode'
            if mode_name not in names:
                missing.append(name)
                continue
            mode = City._meta.get_field(mode_name)
            self.assertTrue(mode.blank)
            self.assertEqual(mode.help_text, MODE_FIELD_HELP)
            self.assertLessEqual(mode.max_length, field.max_length)
        self.assertEqual(missing, [])
        self.assertIn('banner_suffix_mode', names)
        self.assertIn('banner_button_mode', names)
        self.assertFalse(any(name.endswith(('_uk', '_ru')) for name in names))

    def test_home_seo_block_modes_exist_and_services_hero_modes(self):
        home_names = {field.name for field in HomePage._meta.fields}
        missing = []
        for field in HomePage._meta.fields:
            name = field.name
            if not name.startswith('seo_block_') or name.endswith('_mode'):
                continue
            if field.get_internal_type() not in _TEXT_TYPES:
                continue
            if f'{name}_mode' not in home_names:
                missing.append(name)
        self.assertEqual(missing, [])
        self.assertIn('seo_block_title_mode', home_names)
        self.assertIn('seo_block_body_mode', home_names)

        words, matches = load_filter_stopwords()
        self.assertIn('крипт', words)
        service_names = {field.name for field in ServicesPage._meta.fields}
        hero_modes = sorted(
            name for name in service_names
            if name.startswith('hero_') and name.endswith('_mode')
        )
        self.assertEqual(hero_modes, ['hero_text_mode'])
        page = ServicesPage.load()
        for field in ServicesPage._meta.fields:
            name = field.name
            if not name.startswith('hero_') or name.endswith('_mode'):
                continue
            if field.get_internal_type() not in _TEXT_TYPES:
                continue
            dirty = matches(field.default) or matches(getattr(page, name))
            self.assertEqual(f'{name}_mode' in service_names, dirty)

    def test_branch_model_has_no_exchange_safe_or_mode_fields(self):
        names = {field.name for field in Branch._meta.fields}
        self.assertNotIn('exchange_safe', names)
        self.assertFalse(any(name.endswith('_mode') for name in names))

    def test_fill_is_idempotent_and_keeps_editor_copy(self):
        city = City.objects.create(name='Київ', slug='kyiv-fill-mode')
        city.banner_title_mode = 'Свій заголовок'
        city.save(update_fields=['banner_title_mode'])
        fill_city_banner_seo_mode(apps, None)
        fill_city_banner_seo_mode(apps, None)
        city.refresh_from_db()
        self.assertEqual(city.banner_title_mode, 'Свій заголовок')
        self.assertEqual(city.banner_suffix_mode, CITY_MODE_COPY['banner_suffix_mode'])
        self.assertEqual(city.banner_button_mode, CITY_MODE_COPY['banner_button_mode'])
        self.assertEqual(city.banner_text_mode, CITY_MODE_COPY['banner_text_mode'])
        self.assertEqual(city.seo_title_mode, CITY_MODE_COPY['seo_title_mode'])
        self.assertEqual(
            city.seo_description_mode,
            CITY_MODE_COPY['seo_description_mode'],
        )
        city.banner_suffix_mode = 'Свій суфікс'
        city.save(update_fields=['banner_suffix_mode'])
        fill_city_banner_seo_mode(apps, None)
        city.refresh_from_db()
        self.assertEqual(city.banner_suffix_mode, 'Свій суфікс')

        home = HomePage.objects.get(pk=1)
        home.seo_block_title_mode = ''
        home.seo_block_body_mode = '   '
        home.articles_lead = ''
        home.save(update_fields=[
            'seo_block_title_mode',
            'seo_block_body_mode',
            'articles_lead',
        ])
        services = ServicesPage.load()
        services.intro = 'Інтро яке не можна затерти'
        services.save(update_fields=['intro'])
        fill_home_seo_mode(apps, None)
        fill_articles_lead(apps, None)
        fill_home_seo_mode(apps, None)
        fill_articles_lead(apps, None)
        home.refresh_from_db()
        services.refresh_from_db()
        self.assertEqual(
            home.seo_block_title_mode,
            HOME_SEO_MODE_COPY['seo_block_title_mode'],
        )
        self.assertEqual(
            home.seo_block_body_mode,
            HOME_SEO_MODE_COPY['seo_block_body_mode'],
        )
        self.assertEqual(home.articles_lead, SERVICES_MENTION_LEAD)
        self.assertEqual(services.intro, 'Інтро яке не можна затерти')
        home.articles_lead = 'Свій лід'
        home.seo_block_body_mode = 'Свій SEO текст'
        home.save(update_fields=['articles_lead', 'seo_block_body_mode'])
        fill_articles_lead(apps, None)
        fill_home_seo_mode(apps, None)
        home.refresh_from_db()
        self.assertEqual(home.articles_lead, 'Свій лід')
        self.assertEqual(home.seo_block_body_mode, 'Свій SEO текст')

    def test_fill_does_not_set_exchange_safe(self):
        review = Review.objects.create(name='Олег', text='Добре', exchange_safe=False)
        fill_city_banner_seo_mode(apps, None)
        fill_home_seo_mode(apps, None)
        fill_articles_lead(apps, None)
        review.refresh_from_db()
        self.assertFalse(review.exchange_safe)
        network = (_ROOT / 'src/network/migrations/0006_city_banner_suffix_and_button_mode.py').read_text(
            encoding='utf-8',
        )
        content = (_ROOT / 'src/content/migrations/0025_home_seo_mode_and_articles_lead.py').read_text(
            encoding='utf-8',
        )
        self.assertIn('fill_city_banner_seo_mode', network)
        self.assertIn('noop_reverse', network)
        self.assertIn('banner_suffix_mode', network)
        self.assertIn('banner_button_mode', network)
        self.assertIn('fill_articles_lead', content)
        self.assertIn('fill_home_seo_mode', content)
        self.assertIn('noop_reverse', content)
        self.assertNotIn('exchange_safe', network)
        self.assertNotIn('exchange_safe', content)
        self.assertNotIn('intro', content)

    def test_filled_copy_has_no_stop_words(self):
        _, matches = load_filter_stopwords()
        home = HomePage._meta
        city = City._meta
        for name, text in {**CITY_MODE_COPY, **HOME_SEO_MODE_COPY}.items():
            self.assertFalse(matches(text), name)
            self.assertTrue(text.strip())
            field = city.get_field(name) if name in CITY_MODE_COPY else home.get_field(name)
            if field.max_length:
                self.assertLessEqual(len(text), field.max_length)
        self.assertTrue(matches(SERVICES_MENTION_LEAD))
        self.assertEqual(SERVICES_MENTION_LEAD, _POSLUHY_LEAD)
        self.assertLessEqual(len(SERVICES_MENTION_LEAD), 400)

    def test_empty_mode_is_hidden_and_filled_mode_replaces_main_text(self):
        city = City.objects.create(
            name='Львів',
            slug='lviv-hidden-mode',
            banner_text='Потрібен переказ готівки',
        )
        for name in CITY_MODE_COPY:
            setattr(city, name, '')
        city.save()
        home = HomePage.objects.get(pk=1)
        home.seo_block_title = 'Обмін валют в Україні'
        home.seo_block_title_mode = ''
        home.seo_block_body_mode = ''
        home.save(update_fields=[
            'seo_block_title',
            'seo_block_title_mode',
            'seo_block_body_mode',
        ])
        self._mode(True)
        for name in (
            'banner_title',
            'banner_suffix',
            'banner_text',
            'banner_button',
            'seo_title',
            'seo_description',
        ):
            self.assertEqual(resolved_text(city, name, 'запасний'), '')
            self.assertEqual(mode_text(city, name), '')
        self.assertEqual(resolved_text(home, 'seo_block_title', 'запасний'), '')
        self.assertEqual(mode_text(home, 'seo_block_body'), '')
        city.banner_text_mode = f"  {CITY_MODE_COPY['banner_text_mode']}  "
        city.save(update_fields=['banner_text_mode'])
        self.assertEqual(
            resolved_text(city, 'banner_text', 'запасний'),
            CITY_MODE_COPY['banner_text_mode'],
        )
        self.assertEqual(resolved_text(city, 'banner_text'), mode_text(city, 'banner_text'))
        _, matches = load_filter_stopwords()
        self.assertFalse(matches(resolved_text(city, 'banner_text')))
        self._mode(False)
        self.assertEqual(resolved_text(city, 'banner_text'), 'Потрібен переказ готівки')
        self.assertEqual(resolved_text(home, 'seo_block_title'), 'Обмін валют в Україні')

    def test_seed_fills_articles_lead_only_when_empty(self):
        seed = (_ROOT / 'src/core/management/commands/seed_demo.py').read_text(
            encoding='utf-8',
        )
        self.assertIn('fill_articles_lead(apps, None)', seed)
        self.assertIn('fill_city_banner_seo_mode(apps, None)', seed)
        self.assertNotIn('home.articles_lead =', seed)
        self.assertIn("if not (services_page.intro or '').strip():", seed)
        home = HomePage.objects.get(pk=1)
        self.assertEqual(home.articles_lead, SERVICES_MENTION_LEAD)

    @unittest.skip('TODO fallback, передано Frontend')
    def test_posluhy_rendered_intro_outside_mode(self):
        self._mode(False)
        home = HomePage.objects.get(pk=1)
        home.articles_lead = ''
        home.save(update_fields=['articles_lead'])
        fill_articles_lead(apps, None)
        home.refresh_from_db()
        self.assertEqual(home.articles_lead, _POSLUHY_LEAD)
        services = ServicesPage.load()
        services.intro = 'Інший вступ послуг'
        services.save(update_fields=['intro'])
        response = self.client.get(reverse('content:services'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        section = re.search(
            r'<section class="articles-section"[\s\S]*?</section>',
            html,
        )
        self.assertIsNotNone(section)
        lead = re.search(
            r'<p class="articles-section__lead">(.*?)</p>',
            section.group(0),
        )
        self.assertIsNotNone(lead)
        self.assertEqual(lead.group(1).strip(), _POSLUHY_LEAD)
        services.refresh_from_db()
        self.assertEqual(services.intro, 'Інший вступ послуг')

    def test_banner_admin_shows_new_mode_fields(self):
        user = User.objects.create_superuser(
            username='city-mode',
            email='city-mode@example.com',
            password='pass-12345',
        )
        self.client.force_login(user)
        city = City.objects.create(name='Одеса', slug='odesa-admin-mode')
        response = self.client.get(
            reverse('admin:network_bannercity_change', args=[city.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Текст після назви міста для режиму «Лише обмін»')
        self.assertContains(response, 'Текст кнопки на банері для режиму «Лише обмін»')
