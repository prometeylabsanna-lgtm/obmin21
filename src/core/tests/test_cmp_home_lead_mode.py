import importlib.util
import os
import re
from pathlib import Path

from django.apps import apps
from django.core.cache import cache
from django.test import TestCase

from src.content.advantages_fields import (
    CMP_MODE_COPY,
    CMP_THEM_HTML,
    CMP_THEM_HTML_MODE,
    CMP_US_HTML,
    CMP_US_HTML_MODE,
    cmp_them_html_for,
    cmp_us_html_for,
)
from src.content.cms_proxies import HomeArticlesSettings, HomeServicesSettings
from src.content.home_copy import (
    ARTICLES_LEAD_MODE,
    HOME_LEAD_MODE,
    SERVICES_LEAD_MODE,
    SERVICES_MENTION_LEAD,
    home_copy_text,
)
from src.content.models import AdvantagesPage, HomePage
from src.content.stage3_fill import fill_cmp_and_home_lead_mode
from src.core.models import SiteSettings

_ENV = 'EXCHANGE_ONLY_MODE'
_LI = re.compile(
    r'<li><span class="k">([^<]*)</span><strong>([^<]*)</strong></li>'
)
# Список скопійовано з:
# /Users/olegbonislavskyi/Sites/Obmin21-wt-filter/src/core/exchange_stopwords.py
_STOPWORDS_SOURCE = Path(
    '/Users/olegbonislavskyi/Sites/Obmin21-wt-filter/src/core/exchange_stopwords.py'
)
STOP_WORDS = (
    'крипт',
    'krypto',
    'crypto',
    'bitcoin',
    'бітко',
    'битко',
    'ethereum',
    'ефіріум',
    'етериум',
    'usdt',
    'usdc',
    'tether',
    'тезер',
    'стейблко',
    'btc',
    'eth',
    'bnb',
    'sol',
    'trx',
    'ton',
    'біткоїн',
    'swift',
    'переказ',
    'transfer',
    'золот',
    'gold',
    'оптов',
    'зношен',
    'електронн валют',
)
_MODE_FIELDS = (
    'cmp_us_html_mode',
    'cmp_them_html_mode',
    'services_lead_mode',
    'articles_lead_mode',
)


def stop_word_hits(*values):
    parts = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text.casefold())
    if not parts:
        return []
    blob = '\n'.join(parts)
    return [word for word in STOP_WORDS if word.casefold() in blob]


def _rows(html):
    return _LI.findall(html)


class CmpHomeLeadModeTests(TestCase):
    def setUp(self):
        self._saved_env = os.environ.get(_ENV)
        os.environ.pop(_ENV, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = self._saved_env
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def test_mode_fields_have_no_language_variants(self):
        advantage_names = {field.name for field in AdvantagesPage._meta.fields}
        home_names = {field.name for field in HomePage._meta.fields}
        self.assertIn('cmp_us_html_mode', advantage_names)
        self.assertIn('cmp_them_html_mode', advantage_names)
        self.assertIn('services_lead_mode', home_names)
        self.assertIn('articles_lead_mode', home_names)
        for name in _MODE_FIELDS:
            self.assertNotIn(f'{name}_ru', advantage_names | home_names)
            self.assertNotIn(f'{name}_uk', advantage_names | home_names)
        self.assertFalse(any(name.endswith(('_ru', '_uk')) for name in advantage_names))
        self.assertFalse(any(name.endswith(('_ru', '_uk')) for name in home_names))

    def test_mode_html_matches_main_structure(self):
        us = _rows(CMP_US_HTML)
        them = _rows(CMP_THEM_HTML)
        us_mode = _rows(CMP_US_HTML_MODE)
        them_mode = _rows(CMP_THEM_HTML_MODE)
        self.assertEqual(len(us), 6)
        self.assertEqual(len(us_mode), len(us))
        self.assertEqual(len(them_mode), len(them))
        labels = [label for label, _value in us_mode]
        self.assertEqual(labels, [label for label, _value in them_mode])
        self.assertEqual(
            labels,
            ['Курс', 'Комісія', 'Фіксація курсу', 'Купюри', 'Готівка', 'Великі суми'],
        )
        self.assertIn('Долар, євро та фунт', CMP_US_HTML_MODE)
        self.assertNotIn('Криптовалюта', CMP_US_HTML_MODE)
        self.assertNotIn('USDT', CMP_US_HTML_MODE)
        self.assertNotIn('Криптовалюта', CMP_THEM_HTML_MODE)

    def test_filled_copy_has_no_stop_words(self):
        self.assertIn('крипт', STOP_WORDS)
        self.assertIn('зношен', STOP_WORDS)
        self.assertIn('переказ', STOP_WORDS)
        self.assertTrue(stop_word_hits(CMP_US_HTML))
        self.assertTrue(stop_word_hits(CMP_THEM_HTML))
        self.assertTrue(stop_word_hits(SERVICES_MENTION_LEAD))
        filled = (
            *CMP_MODE_COPY.values(),
            *HOME_LEAD_MODE.values(),
        )
        for text in filled:
            self.assertEqual(stop_word_hits(text), [])
            self.assertTrue(text.strip())
        self.assertLessEqual(len(SERVICES_LEAD_MODE), 400)
        self.assertLessEqual(len(ARTICLES_LEAD_MODE), 400)
        if _STOPWORDS_SOURCE.is_file():
            spec = importlib.util.spec_from_file_location(
                'eo_filter_exchange_stopwords',
                _STOPWORDS_SOURCE,
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(tuple(module.STOP_WORDS), STOP_WORDS)

    def test_migration_filled_existing_home_and_fill_is_idempotent(self):
        home = HomePage.objects.get(pk=1)
        self.assertEqual(home.services_lead_mode, SERVICES_LEAD_MODE)
        self.assertEqual(home.articles_lead_mode, ARTICLES_LEAD_MODE)
        self.assertIn('переказ', home.services_lead.casefold())
        self.assertIn('переказ', home.articles_lead.casefold())

        page = AdvantagesPage.load()
        page.cmp_us_html = '<ul><li>своє</li></ul>'
        page.cmp_them_html = '<ul><li>їхнє</li></ul>'
        page.cmp_us_html_mode = '   '
        page.cmp_them_html_mode = ''
        page.save(update_fields=[
            'cmp_us_html',
            'cmp_them_html',
            'cmp_us_html_mode',
            'cmp_them_html_mode',
        ])
        home.services_lead = 'Свій лід'
        home.articles_lead = 'Свої статті'
        home.services_lead_mode = ''
        home.articles_lead_mode = '   '
        home.save(update_fields=[
            'services_lead',
            'articles_lead',
            'services_lead_mode',
            'articles_lead_mode',
        ])

        fill_cmp_and_home_lead_mode(apps, None)
        fill_cmp_and_home_lead_mode(apps, None)
        page.refresh_from_db()
        home.refresh_from_db()
        self.assertEqual(page.cmp_us_html, '<ul><li>своє</li></ul>')
        self.assertEqual(page.cmp_them_html, '<ul><li>їхнє</li></ul>')
        self.assertEqual(page.cmp_us_html_mode, CMP_US_HTML_MODE)
        self.assertEqual(page.cmp_them_html_mode, CMP_THEM_HTML_MODE)
        self.assertEqual(home.services_lead, 'Свій лід')
        self.assertEqual(home.articles_lead, 'Свої статті')
        self.assertEqual(home.services_lead_mode, SERVICES_LEAD_MODE)
        self.assertEqual(home.articles_lead_mode, ARTICLES_LEAD_MODE)

        page.cmp_us_html_mode = '<ul><li>редактор</li></ul>'
        page.cmp_them_html_mode = '<ul><li>редактор їх</li></ul>'
        page.save(update_fields=['cmp_us_html_mode', 'cmp_them_html_mode'])
        home.services_lead_mode = 'Свій режим послуг'
        home.articles_lead_mode = 'Свій режим статей'
        home.save(update_fields=['services_lead_mode', 'articles_lead_mode'])
        fill_cmp_and_home_lead_mode(apps, None)
        page.refresh_from_db()
        home.refresh_from_db()
        self.assertEqual(page.cmp_us_html_mode, '<ul><li>редактор</li></ul>')
        self.assertEqual(page.cmp_them_html_mode, '<ul><li>редактор їх</li></ul>')
        self.assertEqual(home.services_lead_mode, 'Свій режим послуг')
        self.assertEqual(home.articles_lead_mode, 'Свій режим статей')

    def test_access_layer_returns_mode_only_when_enabled(self):
        page = AdvantagesPage.load()
        page.cmp_us_html = CMP_US_HTML
        page.cmp_them_html = CMP_THEM_HTML
        page.cmp_us_html_mode = ''
        page.cmp_them_html_mode = ''
        page.save(update_fields=[
            'cmp_us_html',
            'cmp_them_html',
            'cmp_us_html_mode',
            'cmp_them_html_mode',
        ])
        home = HomePage.load()
        home.services_lead = SERVICES_MENTION_LEAD
        home.articles_lead = SERVICES_MENTION_LEAD
        home.services_lead_mode = ''
        home.articles_lead_mode = ''
        home.save(update_fields=[
            'services_lead',
            'articles_lead',
            'services_lead_mode',
            'articles_lead_mode',
        ])

        self._mode(False)
        self.assertEqual(cmp_us_html_for(page), CMP_US_HTML)
        self.assertEqual(cmp_them_html_for(page), CMP_THEM_HTML)
        self.assertEqual(home_copy_text(home, 'services_lead'), SERVICES_MENTION_LEAD)
        self.assertEqual(home_copy_text(home, 'articles_lead'), SERVICES_MENTION_LEAD)
        self.assertEqual(
            HomeServicesSettings.load().resolved_services_lead(),
            SERVICES_MENTION_LEAD,
        )
        self.assertEqual(
            HomeArticlesSettings.load().resolved_articles_lead(),
            SERVICES_MENTION_LEAD,
        )

        self._mode(True)
        self.assertEqual(cmp_us_html_for(page), '')
        self.assertEqual(cmp_them_html_for(page), '')
        self.assertEqual(home_copy_text(home, 'services_lead'), '')
        self.assertEqual(home_copy_text(home, 'articles_lead'), '')
        self.assertEqual(HomeServicesSettings.load().resolved_services_lead(), '')
        self.assertEqual(HomeArticlesSettings.load().resolved_articles_lead(), '')

        page.cmp_us_html_mode = CMP_US_HTML_MODE
        page.cmp_them_html_mode = CMP_THEM_HTML_MODE
        page.save(update_fields=['cmp_us_html_mode', 'cmp_them_html_mode'])
        home.services_lead_mode = SERVICES_LEAD_MODE
        home.articles_lead_mode = ARTICLES_LEAD_MODE
        home.save(update_fields=['services_lead_mode', 'articles_lead_mode'])

        self.assertEqual(cmp_us_html_for(page), CMP_US_HTML_MODE)
        self.assertEqual(cmp_them_html_for(page), CMP_THEM_HTML_MODE)
        self.assertEqual(
            HomeServicesSettings.load().resolved_services_lead(),
            SERVICES_LEAD_MODE,
        )
        self.assertEqual(
            HomeArticlesSettings.load().resolved_articles_lead(),
            ARTICLES_LEAD_MODE,
        )
        self.assertEqual(home_copy_text(home, 'services_lead'), SERVICES_LEAD_MODE)
        self.assertEqual(home_copy_text(home, 'articles_lead'), ARTICLES_LEAD_MODE)
        for text in (
            cmp_us_html_for(page),
            cmp_them_html_for(page),
            home_copy_text(home, 'services_lead'),
            home_copy_text(home, 'articles_lead'),
        ):
            self.assertEqual(stop_word_hits(text), [])

        self._mode(False)
        self.assertEqual(cmp_us_html_for(page), CMP_US_HTML)
        self.assertEqual(cmp_them_html_for(page), CMP_THEM_HTML)
        self.assertEqual(home_copy_text(home, 'services_lead'), SERVICES_MENTION_LEAD)
        self.assertEqual(home_copy_text(home, 'articles_lead'), SERVICES_MENTION_LEAD)

    def test_migration_calls_fill_and_does_not_set_exchange_safe(self):
        root = Path(__file__).resolve().parents[3]
        content = (root / 'src/content/migrations/0024_cmp_and_home_lead_mode.py').read_text(
            encoding='utf-8',
        )
        self.assertIn('fill_cmp_and_home_lead_mode', content)
        self.assertIn('noop_reverse', content)
        self.assertNotIn('exchange_safe', content)
        for name in _MODE_FIELDS:
            self.assertIn(name, CMP_MODE_COPY.keys() | HOME_LEAD_MODE.keys())
