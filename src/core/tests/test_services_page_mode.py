import importlib.util
import os
from pathlib import Path

from django.apps import apps
from django.core.cache import cache
from django.test import TestCase

from src.content.models import ServicesPage
from src.content.stage3_fill import (
    SERVICES_PAGE_MODE_COPY,
    fill_services_page_mode,
)
from src.core.exchange_fields import resolved_text
from src.core.models import SiteSettings

_ENV = 'EXCHANGE_ONLY_MODE'
_STOPWORDS_PATH = Path(
    '/Users/olegbonislavskyi/Sites/Obmin21-wt-filter/src/core/exchange_stopwords.py'
)


def load_filter_stopwords():
    """Стоп-слова з гілки eo/filter. Список у тесті не копіюється."""
    spec = importlib.util.spec_from_file_location(
        'eo_filter_exchange_stopwords',
        _STOPWORDS_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.STOP_WORDS, module.matches_stop_words


class ServicesPageModeTests(TestCase):
    def setUp(self):
        self._saved_env = os.environ.get(_ENV)
        os.environ.pop(_ENV, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)
        self.page = ServicesPage.load()

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
        names = {field.name for field in ServicesPage._meta.fields}
        self.assertIn('seo_description_mode', names)
        self.assertIn('hero_text_mode', names)
        self.assertFalse(any(name.endswith(('_uk', '_ru')) for name in names))
        hero = ServicesPage._meta.get_field('hero_text_mode')
        seo = ServicesPage._meta.get_field('seo_description_mode')
        self.assertEqual(hero.max_length, 320)
        self.assertEqual(seo.max_length, 320)
        self.assertTrue(hero.blank)
        self.assertTrue(seo.blank)

    def test_fill_is_idempotent_and_keeps_editor_copy(self):
        self.page.hero_text_mode = ''
        self.page.seo_description_mode = ''
        self.page.save(update_fields=['hero_text_mode', 'seo_description_mode'])
        fill_services_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(
            self.page.hero_text_mode,
            SERVICES_PAGE_MODE_COPY['hero_text_mode'],
        )
        self.assertEqual(
            self.page.seo_description_mode,
            SERVICES_PAGE_MODE_COPY['seo_description_mode'],
        )
        snapshot = (self.page.hero_text_mode, self.page.seo_description_mode)
        fill_services_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(
            (self.page.hero_text_mode, self.page.seo_description_mode),
            snapshot,
        )
        self.page.hero_text_mode = 'Свій банер'
        self.page.seo_description_mode = 'Свій опис'
        self.page.save(update_fields=['hero_text_mode', 'seo_description_mode'])
        fill_services_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(self.page.hero_text_mode, 'Свій банер')
        self.assertEqual(self.page.seo_description_mode, 'Свій опис')

    def test_filled_copy_has_no_stop_words(self):
        stop_words, matches_stop_words = load_filter_stopwords()
        self.assertIn('крипт', stop_words)
        self.assertIn('swift', stop_words)
        self.assertIn('переказ', stop_words)
        self.assertIn('золот', stop_words)
        self.assertIn('оптов', stop_words)
        self.assertIn('зношен', stop_words)
        dirty = ServicesPage._meta.get_field('hero_text').default
        self.assertTrue(matches_stop_words(dirty))
        for text in SERVICES_PAGE_MODE_COPY.values():
            self.assertFalse(matches_stop_words(text))
            self.assertLessEqual(len(text), 320)
            self.assertTrue(text.strip())

    def test_resolved_text_uses_mode_only_when_enabled(self):
        self.page.hero_text = 'Обмін валют і перекази'
        self.page.hero_text_mode = SERVICES_PAGE_MODE_COPY['hero_text_mode']
        self.page.seo_description = 'Перекази по Україні'
        self.page.seo_description_mode = SERVICES_PAGE_MODE_COPY['seo_description_mode']
        self.page.save()
        self._mode(False)
        self.assertEqual(resolved_text(self.page, 'hero_text'), self.page.hero_text)
        self.assertEqual(
            resolved_text(self.page, 'seo_description'),
            self.page.seo_description,
        )
        self._mode(True)
        self.assertEqual(
            resolved_text(self.page, 'hero_text'),
            SERVICES_PAGE_MODE_COPY['hero_text_mode'],
        )
        self.assertEqual(
            resolved_text(self.page, 'seo_description'),
            SERVICES_PAGE_MODE_COPY['seo_description_mode'],
        )
        _, matches_stop_words = load_filter_stopwords()
        self.assertFalse(matches_stop_words(resolved_text(self.page, 'hero_text')))
        self.assertFalse(
            matches_stop_words(resolved_text(self.page, 'seo_description')),
        )

    def test_resolved_text_in_mode_equals_mode_text(self):
        from src.core.exchange_mode import mode_text

        class Row:
            def __init__(self, **fields):
                self.__dict__.update(fields)

        self._mode(True)
        spaced = Row(hero_text='основний', hero_text_mode='  Лише готівка  ')
        empty = Row(hero_text='основний', hero_text_mode=None)
        missing = Row(title='без mode-поля')
        for row, name in (
            (spaced, 'hero_text'),
            (empty, 'hero_text'),
            (missing, 'title'),
        ):
            self.assertEqual(resolved_text(row, name), mode_text(row, name))
            self.assertEqual(
                resolved_text(row, name, 'запасний'),
                mode_text(row, name),
            )
        self.assertEqual(resolved_text(spaced, 'hero_text'), 'Лише готівка')
        self.assertEqual(resolved_text(empty, 'hero_text'), '')
        self.assertEqual(resolved_text(missing, 'title', 'запасний'), '')
        self.page.hero_text = 'основний'
        self.page.hero_text_mode = '  Лише готівка  '
        self.page.save(update_fields=['hero_text', 'hero_text_mode'])
        self.assertEqual(
            resolved_text(self.page, 'hero_text', 'запасний'),
            mode_text(self.page, 'hero_text'),
        )

    def test_migration_calls_fill_and_noop_reverse(self):
        root = Path(__file__).resolve().parents[3]
        content = '\n'.join(
            path.read_text(encoding='utf-8')
            for path in (root / 'src/content/migrations').glob('0022_*.py')
        )
        self.assertIn('fill_services_page_mode', content)
        self.assertIn('noop_reverse', content)
        self.assertIn('hero_text_mode', content)
