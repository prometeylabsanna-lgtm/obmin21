import os
import re
from pathlib import Path

from django.apps import apps
from django.contrib import admin
from django.core.cache import cache
from django.db.models import ImageField
from django.test import TestCase

import src.content.admin  # noqa: F401
from src.content.advantages_fields import (
    CMP_THEM_HTML_MODE,
    CMP_US_HTML_MODE,
    advantage_default,
    advantage_text,
    stat_text_for,
)
from src.content.advantages_mode_copy import (
    choose_mode_text,
    fill_advantages_page_mode,
    image_is_neutral,
    iter_mode_targets,
)
from src.content.models import AdvantagesPage, CookiePage, OfferPage, PrivacyPage
from src.core.exchange_fields import MODE_FIELD_HELP, resolved_text
from src.core.exchange_mode import mode_text
from src.core.exchange_stopwords import matches_stop_words
from src.core.models import SiteSettings
from src.core.tests.test_services_page_mode import load_filter_stopwords

_ENV = 'EXCHANGE_ONLY_MODE'
_ROOT = Path(__file__).resolve().parents[3]
_STAT_NUMBER = re.compile(r'stat_\d+_number\Z')


def _follows(fields, base):
    names = list(fields)
    return names[names.index(base) + 1] == f'{base}_mode'


def _fieldset_fields(model):
    model_admin = admin.site._registry[model]
    names = []
    for _title, opts in model_admin.content_fieldsets:
        names.extend(opts.get('fields') or ())
    return names


class AdvantagesPageModeTests(TestCase):
    def setUp(self):
        self._saved_env = os.environ.get(_ENV)
        os.environ.pop(_ENV, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)
        cache.clear()
        self.page = AdvantagesPage.load()

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = self._saved_env
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def test_mode_fields_follow_bases_in_admin(self):
        names = {field.name for field in AdvantagesPage._meta.fields}
        self.assertFalse(any(_STAT_NUMBER.fullmatch(name) for name in names))
        for blocked in (
            'stat_2_title_mode',
            'stat_2_number_mode',
            'hero_banner_mode',
            'color_why_banner_mode',
            'intro_mode',
        ):
            self.assertNotIn(blocked, names)
        for model in (PrivacyPage, OfferPage, CookiePage):
            legal = {field.name for field in model._meta.fields}
            self.assertNotIn('body_mode', legal)
        form_fields = _fieldset_fields(AdvantagesPage)
        targets = list(iter_mode_targets(AdvantagesPage))
        self.assertTrue(targets)
        for base, kind in targets:
            mode_name = f'{base}_mode'
            self.assertIn(mode_name, names)
            self.assertTrue(_follows(form_fields, base), base)
            base_field = AdvantagesPage._meta.get_field(base)
            mode_field = AdvantagesPage._meta.get_field(mode_name)
            self.assertTrue(mode_field.blank)
            self.assertEqual(mode_field.help_text, MODE_FIELD_HELP)
            if kind == 'image':
                self.assertIsInstance(mode_field, ImageField)
                self.assertEqual(mode_field.upload_to, 'advantages/')
            elif base_field.get_internal_type() == 'CharField':
                self.assertEqual(mode_field.get_internal_type(), 'CharField')
                self.assertEqual(mode_field.max_length, base_field.max_length)
            else:
                self.assertEqual(mode_field.get_internal_type(), 'TextField')

    def test_fill_is_idempotent_and_has_no_stopwords(self):
        _words, filter_matches = load_filter_stopwords()
        targets = list(iter_mode_targets(AdvantagesPage))
        text_modes = [f'{base}_mode' for base, kind in targets if kind == 'text']
        AdvantagesPage.objects.filter(pk=self.page.pk).update(
            **{name: '' for name in text_modes},
            why_banner='',
            why_banner_mode='',
            why_coins='advantages/coins.png',
            why_coins_mode='',
        )
        written = fill_advantages_page_mode(apps, None)
        again = fill_advantages_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(again, {})
        self.assertEqual(set(written), set(text_modes))
        self.assertFalse(self.page.why_banner_mode)
        self.assertFalse(self.page.why_coins_mode)
        self.assertFalse(getattr(self.page, 'exchange_safe', False))
        for mode_name, text in written.items():
            self.assertEqual(getattr(self.page, mode_name), text)
            self.assertFalse(matches_stop_words(text), text)
            self.assertFalse(filter_matches(text), text)
            base = mode_name[:-5]
            self.assertEqual(
                text,
                choose_mode_text(
                    advantage_default(base) if base not in (
                        'cmp_us_html', 'cmp_them_html',
                    ) else getattr(self.page, base),
                    advantage_default(base),
                    {
                        'cmp_us_html': CMP_US_HTML_MODE,
                        'cmp_them_html': CMP_THEM_HTML_MODE,
                    }.get(base, ''),
                ),
            )
        self.assertEqual(written['cmp_us_html_mode'], CMP_US_HTML_MODE)
        self.assertEqual(written['cmp_them_html_mode'], CMP_THEM_HTML_MODE)
        self.assertEqual(written['stat_2_text_mode'], advantage_default('stat_2_text'))
        self.assertEqual(written['why_lead_mode'], advantage_default('why_lead'))

        self.page.why_lead_mode = 'Свій лід обміну готівки'
        self.page.cmp_btn_mode = 'Своя кнопка'
        self.page.save(update_fields=['why_lead_mode', 'cmp_btn_mode'])
        fill_advantages_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(self.page.why_lead_mode, 'Свій лід обміну готівки')
        self.assertEqual(self.page.cmp_btn_mode, 'Своя кнопка')
        self.assertEqual(self.page.stat_2_text_mode, written['stat_2_text_mode'])

    def test_dirty_or_empty_base_gets_clean_text(self):
        self.page.stat_2_text = 'Обмін криптовалюти та перекази золота'
        self.page.stat_2_text_mode = '   '
        self.page.stat_3_text = ''
        self.page.stat_3_text_mode = ''
        self.page.why_3_text = 'Приймаємо зношені купюри'
        self.page.why_3_text_mode = ''
        self.page.save(update_fields=[
            'stat_2_text',
            'stat_2_text_mode',
            'stat_3_text',
            'stat_3_text_mode',
            'why_3_text',
            'why_3_text_mode',
        ])
        written = fill_advantages_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(written['stat_2_text_mode'], advantage_default('stat_2_text'))
        self.assertEqual(self.page.stat_2_text_mode, advantage_default('stat_2_text'))
        self.assertEqual(self.page.stat_3_text_mode, advantage_default('stat_3_text'))
        self.assertEqual(self.page.why_3_text_mode, advantage_default('why_3_text'))
        self.assertNotEqual(self.page.stat_2_text_mode, self.page.stat_2_text)
        for text in (
            self.page.stat_2_text_mode,
            self.page.stat_3_text_mode,
            self.page.why_3_text_mode,
        ):
            self.assertFalse(matches_stop_words(text), text)
        self.assertEqual(choose_mode_text('', '', ''), '')

    def test_images_stay_empty_unless_neutral(self):
        self.assertFalse(image_is_neutral(''))
        self.assertFalse(image_is_neutral('advantages/coins.png'))
        self.assertFalse(image_is_neutral('images/crypto-card.webp'))
        self.assertFalse(image_is_neutral('advantages/bitcoin.jpg'))
        self.assertFalse(image_is_neutral('advantages/ETH.png'))
        self.assertFalse(image_is_neutral('advantages/gold-bar.png'))
        self.assertTrue(image_is_neutral('advantages/branch-hall.jpg'))
        AdvantagesPage.objects.filter(pk=self.page.pk).update(
            why_banner='advantages/coins.png',
            why_banner_mode='',
            why_coins='advantages/crypto-btc.png',
            why_coins_mode='',
        )
        written = fill_advantages_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertNotIn('why_banner_mode', written)
        self.assertNotIn('why_coins_mode', written)
        self.assertFalse(self.page.why_banner_mode)
        self.assertFalse(self.page.why_coins_mode)
        AdvantagesPage.objects.filter(pk=self.page.pk).update(
            why_banner='advantages/branch-hall.jpg',
            why_banner_mode='',
            why_coins='advantages/office-desk.jpg',
            why_coins_mode='',
        )
        written = fill_advantages_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(written['why_banner_mode'], 'advantages/branch-hall.jpg')
        self.assertEqual(written['why_coins_mode'], 'advantages/office-desk.jpg')
        self.assertEqual(self.page.why_banner_mode.name, 'advantages/branch-hall.jpg')
        self.assertEqual(self.page.why_coins_mode.name, 'advantages/office-desk.jpg')
        AdvantagesPage.objects.filter(pk=self.page.pk).update(
            why_banner='advantages/other-hall.jpg',
            why_banner_mode='advantages/kept-hall.jpg',
        )
        fill_advantages_page_mode(apps, None)
        self.page.refresh_from_db()
        self.assertEqual(self.page.why_banner_mode.name, 'advantages/kept-hall.jpg')

    def test_mode_text_hides_base_until_mode_is_set(self):
        self.page.stat_2_text = 'База відділень'
        self.page.stat_2_text_mode = '  Готівкові відділення  '
        self.page.why_lead = 'База з криптовалютою'
        self.page.why_lead_mode = '  Обмін готівки у відділенні  '
        self.page.why_1_title = 'Криптовалюта'
        self.page.why_1_title_mode = 'Без комісії'
        self.page.why_1_text = 'USDT на готівку'
        self.page.why_1_text_mode = 'Сума в касі дорівнює сумі в заявці'
        self.page.cmp_btn = 'Зафіксувати'
        self.page.cmp_btn_mode = ''
        self.page.save()
        self._mode(False)
        self.assertEqual(mode_text(self.page, 'why_lead'), 'База з криптовалютою')
        self.assertEqual(advantage_text(self.page, 'why_lead'), 'База з криптовалютою')
        self.assertEqual(stat_text_for(self.page, 2), 'База відділень')
        self.assertEqual(
            resolved_text(self.page, 'cmp_btn', 'Зафіксувати курс'),
            'Зафіксувати',
        )
        self._mode(True)
        self.assertEqual(mode_text(self.page, 'stat_2_text'), 'Готівкові відділення')
        self.assertEqual(stat_text_for(self.page, 2), 'Готівкові відділення')
        self.assertEqual(
            advantage_text(self.page, 'why_lead'),
            'Обмін готівки у відділенні',
        )
        self.assertEqual(
            resolved_text(self.page, 'why_lead', 'запасний'),
            mode_text(self.page, 'why_lead'),
        )
        rows = {row['title']: row['text'] for row in self.page.iter_why()}
        self.assertEqual(rows['Без комісії'], 'Сума в касі дорівнює сумі в заявці')
        self.assertNotIn('Криптовалюта', rows)
        self.assertEqual(advantage_text(self.page, 'cmp_btn'), '')
        self.assertEqual(self.page.why_banner_src(), '')
        self.page.stat_2_text_mode = ''
        self.page.why_lead_mode = '   '
        self.page.save(update_fields=['stat_2_text_mode', 'why_lead_mode'])
        self.assertEqual(stat_text_for(self.page, 2), '')
        self.assertEqual(advantage_text(self.page, 'why_lead'), '')
        self._mode(False)
        self.assertEqual(mode_text(self.page, 'stat_2_text'), 'База відділень')
        self.assertEqual(advantage_text(self.page, 'why_lead'), 'База з криптовалютою')

    def test_migration_and_seed_call_fill_without_exchange_safe(self):
        migration = next((
            _ROOT / 'src/content/migrations'
        ).glob('*_advantages_page_mode_fields.py'))
        content = migration.read_text(encoding='utf-8')
        seed = (
            _ROOT / 'src/core/management/commands/seed_demo.py'
        ).read_text(encoding='utf-8')
        copy_src = (
            _ROOT / 'src/content/advantages_mode_copy.py'
        ).read_text(encoding='utf-8')
        self.assertIn('fill_advantages_page_mode', content)
        self.assertIn('noop_reverse', content)
        self.assertIn('why_lead_mode', content)
        self.assertIn('stat_2_text_mode', content)
        self.assertIn('cmp_btn_mode', content)
        self.assertNotIn('body_mode', content)
        for source in (content, seed, copy_src):
            self.assertNotIn('exchange_safe', source)
        self.assertIn('fill_advantages_page_mode(apps, None)', seed)

    def test_missing_page_is_left_alone(self):
        AdvantagesPage.objects.filter(pk=1).delete()
        self.assertEqual(fill_advantages_page_mode(apps, None), {})
