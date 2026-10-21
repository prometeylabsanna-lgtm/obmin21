import copy
import os
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.core.cache import cache
from django.test import TestCase

from src.blog.article_data import BY_SLUG, layout_for
from src.blog.models import Category, Post
from src.content.advantages_fields import (
    CMP_US_HTML,
    STAT_1_TEXT,
    cmp_us_html_for,
    stat_text_for,
)
from src.content.cms_proxies import HomeServicesSettings
from src.content.home_copy import HOME_COPY_DEFAULTS, home_copy_text
from src.content.models import AdvantagesPage, HomePage, Service
from src.content.service_blocks import SERVICE_BLOCK_DEFAULTS, SERVICE_BLOCKS
from src.content.stage3_fill import fill_article_layouts, fill_content_copy
from src.core.models import SiteSettings

_ENV = 'EXCHANGE_ONLY_MODE'


class Stage3CopyTests(TestCase):
    def setUp(self):
        self._saved_env = os.environ.get(_ENV)
        os.environ.pop(_ENV, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)
        self.category = Category.objects.create(name='Поради', slug='porady-stage3')

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = self._saved_env
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)

    def _service(self, slug='obmin-valyut', **extra):
        payload = {
            'title': 'Обмін валют',
            'slug': slug,
            'short_desc': 'Коротко',
        }
        payload.update(extra)
        return Service.objects.create(**payload)

    def _post(self, slug='kurs-dolara-2027'):
        return Post.objects.create(
            category=self.category,
            title='Курс долара',
            slug=slug,
            body='Текст',
        )

    def test_fill_service_blocks_and_second_run_keeps_them(self):
        service = self._service()
        fill_content_copy(apps, None)
        service.refresh_from_db()
        default = SERVICE_BLOCK_DEFAULTS['obmin-valyut']
        self.assertEqual(service.block_text, default['text'])
        self.assertEqual(tuple(service.block_points.split('\n')), default['points'])
        self.assertEqual(service.block_cta, default['cta'])
        snapshot = (service.block_text, service.block_points, service.block_cta)
        fill_content_copy(apps, None)
        service.refresh_from_db()
        self.assertEqual(
            (service.block_text, service.block_points, service.block_cta),
            snapshot,
        )

    def test_fill_does_not_overwrite_editor_copy(self):
        service = self._service(block_text='Свій текст', block_cta='Своя')
        page = AdvantagesPage.load()
        page.cmp_us_html = '<ul><li>своє</li></ul>'
        page.stat_1_text = 'Своя статистика'
        page.save(update_fields=['cmp_us_html', 'stat_1_text'])
        home = HomePage.load()
        home.services_lead = 'Свій лід'
        home.save(update_fields=['services_lead'])
        fill_content_copy(apps, None)
        service.refresh_from_db()
        page.refresh_from_db()
        home.refresh_from_db()
        self.assertEqual(service.block_text, 'Свій текст')
        self.assertEqual(service.block_cta, 'Своя')
        self.assertEqual(page.cmp_us_html, '<ul><li>своє</li></ul>')
        self.assertEqual(page.stat_1_text, 'Своя статистика')
        self.assertEqual(home.services_lead, 'Свій лід')

    def test_fill_restores_empty_page_copy(self):
        page = AdvantagesPage.load()
        page.cmp_us_html = ''
        page.stat_1_text = ''
        page.save(update_fields=['cmp_us_html', 'stat_1_text'])
        home = HomePage.load()
        home.services_lead = ''
        home.articles_lead = ''
        home.save(update_fields=['services_lead', 'articles_lead'])
        fill_content_copy(apps, None)
        fill_content_copy(apps, None)
        page.refresh_from_db()
        home.refresh_from_db()
        self.assertEqual(page.cmp_us_html, CMP_US_HTML)
        self.assertEqual(page.stat_1_text, STAT_1_TEXT)
        self.assertEqual(home.services_lead, HOME_COPY_DEFAULTS['services_lead'])
        self.assertEqual(home.articles_lead, HOME_COPY_DEFAULTS['articles_lead'])

    def test_fill_article_layout_is_idempotent(self):
        slug = 'kurs-dolara-2027'
        post = self._post(slug)
        fill_article_layouts(apps, None)
        post.refresh_from_db()
        self.assertEqual(post.layout['h1a'], BY_SLUG[slug]['h1a'])
        self.assertEqual(post.layout['sections'], BY_SLUG[slug]['sections'])
        snapshot = copy.deepcopy(post.layout)
        fill_article_layouts(apps, None)
        post.refresh_from_db()
        self.assertEqual(post.layout, snapshot)
        post.layout = {
            'h1a': 'Своє',
            'h1b': '',
            'lead': '',
            'read': '1 хв',
            'sections': [],
            'fig_cap': '',
            'fig_slug': slug,
        }
        post.save(update_fields=['layout'])
        fill_article_layouts(apps, None)
        post.refresh_from_db()
        self.assertEqual(post.layout['h1a'], 'Своє')

    def test_service_blocks_fall_back_when_fields_empty(self):
        self._service()
        default = SERVICE_BLOCK_DEFAULTS['obmin-valyut']
        block = SERVICE_BLOCKS.get('obmin-valyut')
        self.assertEqual(block['text'], default['text'])
        self.assertEqual(block['points'], default['points'])
        self.assertEqual(block['cta'], default['cta'])
        self._service(slug='perekazy-po-ukraini', title='Перекази')
        self.assertEqual(SERVICE_BLOCKS.get('perekazy-po-ukraini', {}), {})

    def test_service_blocks_prefer_database(self):
        self._service(block_text='З бази', block_points='А\nБ', block_cta='Кнопка')
        block = SERVICE_BLOCKS.get('obmin-valyut')
        self.assertEqual(block['text'], 'З бази')
        self.assertEqual(block['points'], ('А', 'Б'))
        self.assertEqual(block['cta'], 'Кнопка')

    def test_service_blocks_mode_returns_variant_or_empty(self):
        service = self._service(
            block_text='Основний',
            block_text_mode='Режимний',
            block_points='Основний пункт',
            block_points_mode='Пункт режиму',
            block_cta='Основна',
            block_cta_mode='Режимна',
        )
        self._mode(True)
        block = SERVICE_BLOCKS.get('obmin-valyut')
        self.assertEqual(block['text'], 'Режимний')
        self.assertEqual(block['points'], ('Пункт режиму',))
        self.assertEqual(block['cta'], 'Режимна')
        service.block_text_mode = ''
        service.block_points_mode = ''
        service.block_cta_mode = ''
        service.save(update_fields=[
            'block_text_mode', 'block_points_mode', 'block_cta_mode',
        ])
        self.assertEqual(
            SERVICE_BLOCKS.get('obmin-valyut'),
            {'text': '', 'points': (), 'cta': ''},
        )

    def test_advantages_and_home_mode_or_fallback(self):
        page = AdvantagesPage.load()
        page.stat_1_text = ''
        page.cmp_us_html = ''
        page.save(update_fields=['stat_1_text', 'cmp_us_html'])
        home = HomePage.load()
        home.services_lead = ''
        home.save(update_fields=['services_lead'])
        self.assertEqual(stat_text_for(page, 1), STAT_1_TEXT)
        self.assertEqual(cmp_us_html_for(page), CMP_US_HTML)
        self.assertIn('криптоактивів', page.iter_stats()[0]['text'])
        self.assertIn('coins.png', page.why_coins_src())
        self.assertEqual(
            home_copy_text(home, 'services_lead'),
            HOME_COPY_DEFAULTS['services_lead'],
        )
        self.assertEqual(
            HomeServicesSettings.load().resolved_services_lead(),
            HOME_COPY_DEFAULTS['services_lead'],
        )
        self._mode(True)
        self.assertEqual(page.why_coins_src(), '')
        self.assertEqual(stat_text_for(page, 1), '')
        self.assertEqual(cmp_us_html_for(page), '')
        self.assertNotIn('криптоактивів', ' '.join(
            row['text'] for row in page.iter_stats()
        ))
        self.assertEqual(home_copy_text(home, 'services_lead'), '')
        page.stat_1_text_mode = 'Лише готівка'
        page.cmp_us_html_mode = '<ul><li>режим</li></ul>'
        page.save(update_fields=['stat_1_text_mode', 'cmp_us_html_mode'])
        home.services_lead_mode = 'Лише обмін валют'
        home.save(update_fields=['services_lead_mode'])
        self.assertEqual(stat_text_for(page, 1), 'Лише готівка')
        self.assertEqual(cmp_us_html_for(page), '<ul><li>режим</li></ul>')
        self.assertEqual(
            HomeServicesSettings.load().resolved_services_lead(),
            'Лише обмін валют',
        )

    def test_article_layout_matches_constant_and_mode(self):
        slug = 'dolar-chy-yevro'
        post = self._post(slug)
        fallback = layout_for(post)
        self.assertEqual(fallback['h1a'], BY_SLUG[slug]['h1a'])
        self.assertEqual(post.reading_label(), BY_SLUG[slug]['read'])
        post.layout = copy.deepcopy(BY_SLUG[slug])
        post.save(update_fields=['layout'])
        self.assertEqual(layout_for(post), fallback)
        post.layout_mode = {
            'h1a': 'Режим',
            'h1b': 'обмін',
            'lead': 'Лід режиму',
            'read': '1 хв',
            'fig_slug': slug,
            'fig_cap': '',
            'sections': [{'h': 'Секція', 'p': ['Абзац'], 'list': []}],
        }
        post.save(update_fields=['layout_mode'])
        self._mode(True)
        layout = layout_for(post)
        self.assertEqual(layout['h1a'], 'Режим')
        self.assertEqual(layout['lead'], 'Лід режиму')
        self.assertEqual(layout['sections'][0]['h'], 'Секція')
        self.assertEqual(post.reading_label(), '1 хв')
        post.layout_mode = None
        post.save(update_fields=['layout_mode'])
        empty = layout_for(post)
        self.assertEqual(empty['h1a'], '')
        self.assertEqual(empty['lead'], '')
        self.assertEqual(empty['sections'], [])
        self.assertEqual(post.reading_label(), '')

    def test_migrations_call_fill_and_noop_reverse(self):
        root = Path(__file__).resolve().parents[3]
        content = '\n'.join(
            path.read_text(encoding='utf-8')
            for path in (root / 'src/content/migrations').glob('*.py')
        )
        blog = '\n'.join(
            path.read_text(encoding='utf-8')
            for path in (root / 'src/blog/migrations').glob('*.py')
        )
        self.assertIn('fill_content_copy', content)
        self.assertIn('noop_reverse', content)
        self.assertIn('fill_article_layouts', blog)
        self.assertIn('noop_reverse', blog)

    def test_env_mode_does_not_use_main_service_text(self):
        self._service(block_text='Основний', block_text_mode='')
        with patch.dict(os.environ, {_ENV: '1'}):
            block = SERVICE_BLOCKS.get('obmin-valyut')
        self.assertEqual(block['text'], '')
        self.assertNotEqual(block['text'], 'Основний')
