from pathlib import Path

from django.apps import apps
from django.contrib import admin
from django.test import TestCase

from src.blog.models import Category, Post
from src.content.admin_items import ServiceAdmin
from src.content.models import (
    AdvantagesPage,
    BlogPage,
    ContactsPage,
    CookiePage,
    FaqPage,
    OfferPage,
    PrivacyPage,
    RatesPage,
    Service,
    ServicesPage,
)
from src.content.page_meta_mode import (
    EXCHANGE_SHORT_DESC_MODE,
    PAGE_MODE_COPY,
    fill_page_meta_mode,
    is_exchange_service,
)
from src.content.service_blocks import SERVICE_BLOCK_DEFAULTS
from src.core.exchange_stopwords import matches_stop_words
from src.core.tests.test_services_page_mode import load_filter_stopwords
from src.rates.models import CurrencyPair
from src.rates.pair_mode_copy import fiat_pair_mode_copy, fill_fiat_pair_mode, is_crypto_pair

_ROOT = Path(__file__).resolve().parents[3]

_REQUESTED = {
    ServicesPage: (
        'title_mode',
        'seo_title_mode',
        'seo_description_mode',
        'intro_mode',
        'hero_text_mode',
    ),
    Service: ('short_desc_mode',),
    AdvantagesPage: (
        'title_mode',
        'hero_lead_mode',
        'seo_title_mode',
        'seo_description_mode',
    ),
    ContactsPage: (
        'seo_title_mode',
        'title_mode',
        'seo_description_mode',
        'heading_mode',
    ),
    FaqPage: (
        'title_mode',
        'lead_mode',
        'seo_title_mode',
        'seo_description_mode',
    ),
    BlogPage: (
        'title_mode',
        'intro_mode',
        'seo_title_mode',
        'seo_description_mode',
    ),
    Post: (
        'seo_title_mode',
        'title_mode',
        'seo_description_mode',
        'excerpt_mode',
    ),
    RatesPage: (
        'title_mode',
        'intro_mode',
        'seo_title_mode',
        'seo_description_mode',
    ),
    CurrencyPair: (
        'seo_title_mode',
        'seo_description_mode',
        'intro_mode',
    ),
}

_LEGAL_MODE_FIELDS = (
    'seo_title_mode',
    'title_mode',
    'seo_description_mode',
    'body_mode',
)

_SKIP_SERVICE_SLUGS = (
    'groshovi-perekazy',
    'kryptovalyuta',
    'investytsiine-zoloto',
    'optovyi-obmin',
    'zamina-znoshenykh-kupiur',
    'swift-peredacha',
)


def _form_fields(model):
    model_admin = admin.site._registry[model]
    names = []
    fieldsets = getattr(model_admin, 'content_fieldsets', None) or getattr(
        model_admin, 'fieldsets', None,
    )
    if fieldsets:
        for _title, opts in fieldsets:
            names.extend(opts.get('fields') or ())
    names.extend(getattr(model_admin, 'content_fields', ()) or ())
    names.extend(getattr(model_admin, 'fields', ()) or ())
    return names


class PageMetaModeTests(TestCase):
    def test_requested_mode_fields_follow_existing_bases(self):
        missing_bases = []
        for model, mode_names in _REQUESTED.items():
            names = {field.name for field in model._meta.fields}
            for mode_name in mode_names:
                base_name = mode_name[:-5]
                if base_name not in names:
                    missing_bases.append(f'{model.__name__}.{base_name}')
                    continue
                self.assertIn(mode_name, names, model.__name__)
                mode = model._meta.get_field(mode_name)
                base = model._meta.get_field(base_name)
                self.assertTrue(mode.blank)
                if base.get_internal_type() == 'CharField':
                    self.assertEqual(mode.max_length, base.max_length)
        self.assertEqual(missing_bases, [])

    def test_legal_pages_keep_main_fields_without_mode_copies(self):
        for model in (PrivacyPage, OfferPage, CookiePage):
            names = {field.name for field in model._meta.fields}
            for mode_name in _LEGAL_MODE_FIELDS:
                self.assertNotIn(mode_name, names, model.__name__)
            self.assertIn('seo_title', names)
            self.assertIn('seo_description', names)
            self.assertIn('body', names)

    def test_mode_fields_are_on_admin_forms(self):
        for model, mode_names in _REQUESTED.items():
            form_fields = _form_fields(model)
            for mode_name in mode_names:
                self.assertIn(mode_name, form_fields, model.__name__)
        for model in (PrivacyPage, OfferPage, CookiePage):
            form_fields = _form_fields(model)
            for mode_name in _LEGAL_MODE_FIELDS:
                self.assertNotIn(mode_name, form_fields, model.__name__)

    def test_service_block_texts_are_admin_fields(self):
        keys = set()
        for block in SERVICE_BLOCK_DEFAULTS.values():
            keys.update(block)
        self.assertEqual(keys, {'text', 'points', 'cta'})
        for name in (
            'block_text',
            'block_text_mode',
            'block_points',
            'block_points_mode',
            'block_cta',
            'block_cta_mode',
        ):
            self.assertIn(name, ServiceAdmin.fields)

    def test_fill_is_idempotent_and_skips_stop_words(self):
        _words, filter_matches = load_filter_stopwords()
        for label, mapping in PAGE_MODE_COPY.items():
            app_label, model_name = label.split('.')
            model = apps.get_model(app_label, model_name)
            row = model.objects.get_or_create(pk=1)[0]
            row.__class__.objects.filter(pk=row.pk).update(
                **{name: '' for name in mapping},
            )
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut',
            short_desc='Коротко',
        )
        kept = Service.objects.create(
            title='Обмін євро',
            slug='obmin-ievro',
            short_desc='Євро',
            short_desc_mode='Свій опис картки',
        )
        skipped = []
        for index, slug in enumerate(_SKIP_SERVICE_SLUGS):
            skipped.append(Service.objects.create(
                title=f'Інше {index}',
                slug=slug,
                short_desc='Текст',
            ))
        usd = CurrencyPair.objects.create(
            code='USD',
            name='Долар США',
            slug='usd-meta-mode',
        )
        pln = CurrencyPair.objects.create(
            code='PLN',
            name='Польський злотий',
            slug='pln-meta-mode',
        )
        usdt = CurrencyPair.objects.create(
            code='USDT/UAH',
            name='Tether',
            slug='usdt-meta-mode',
            base_code='UAH',
        )
        category = Category.objects.create(name='Поради', slug='porady-meta-mode')
        post = Post.objects.create(
            category=category,
            title='Курс долара',
            slug='kurs-dolara-meta-mode',
            body='Текст статті',
            excerpt='Анонс',
            seo_title='SEO',
            seo_description='Опис',
        )

        fill_page_meta_mode(apps, None)
        fill_fiat_pair_mode(apps, None)
        fill_page_meta_mode(apps, None)
        fill_fiat_pair_mode(apps, None)

        filled = []
        for label, mapping in PAGE_MODE_COPY.items():
            app_label, model_name = label.split('.')
            model = apps.get_model(app_label, model_name)
            row = model.objects.get(pk=1)
            for name, text in mapping.items():
                self.assertEqual(getattr(row, name), text, f'{label}.{name}')
                filled.append(text)
        exchange = Service.objects.get(slug='obmin-valyut')
        self.assertEqual(exchange.short_desc_mode, EXCHANGE_SHORT_DESC_MODE)
        self.assertFalse(exchange.exchange_safe)
        filled.append(EXCHANGE_SHORT_DESC_MODE)
        kept.refresh_from_db()
        self.assertEqual(kept.short_desc_mode, 'Свій опис картки')
        for row in skipped:
            row.refresh_from_db()
            self.assertEqual(row.short_desc_mode, '')
            self.assertFalse(is_exchange_service(row))
        usd.refresh_from_db()
        pln.refresh_from_db()
        usdt.refresh_from_db()
        post.refresh_from_db()
        self.assertFalse(is_crypto_pair(usd))
        self.assertFalse(is_crypto_pair(pln))
        self.assertTrue(is_crypto_pair(usdt))
        for pair in (usd, pln):
            copy = fiat_pair_mode_copy(pair.code)
            for name, text in copy.items():
                self.assertEqual(getattr(pair, name), text)
                filled.append(text)
            self.assertFalse(pair.exchange_safe)
        for name in _REQUESTED[CurrencyPair]:
            self.assertEqual(getattr(usdt, name), '')
        for name in _REQUESTED[Post]:
            self.assertEqual(getattr(post, name), '')
        self.assertFalse(post.exchange_safe)

        hits = [text for text in filled if matches_stop_words(text) or filter_matches(text)]
        self.assertEqual(hits, [])

        ServicesPage.objects.filter(pk=1).update(title_mode='Свій заголовок')
        usd.seo_title_mode = 'Свій курс'
        usd.save(update_fields=['seo_title_mode'])
        fill_page_meta_mode(apps, None)
        fill_fiat_pair_mode(apps, None)
        page = ServicesPage.objects.get(pk=1)
        usd.refresh_from_db()
        self.assertEqual(page.title_mode, 'Свій заголовок')
        self.assertEqual(page.seo_title_mode, PAGE_MODE_COPY['content.ServicesPage']['seo_title_mode'])
        self.assertEqual(usd.seo_title_mode, 'Свій курс')
        self.assertEqual(usd.intro_mode, fiat_pair_mode_copy('USD')['intro_mode'])

    def test_migrations_are_fill_empty_and_seed_calls_them(self):
        content = (
            _ROOT / 'src/content/migrations/0026_page_title_meta_mode.py'
        ).read_text(encoding='utf-8')
        blog = (
            _ROOT / 'src/blog/migrations/0007_post_title_meta_mode.py'
        ).read_text(encoding='utf-8')
        rates = (
            _ROOT / 'src/rates/migrations/0006_pair_meta_mode.py'
        ).read_text(encoding='utf-8')
        seed = (
            _ROOT / 'src/core/management/commands/seed_demo.py'
        ).read_text(encoding='utf-8')
        self.assertIn('fill_page_meta_mode', content)
        self.assertIn('noop_reverse', content)
        self.assertIn('fill_fiat_pair_mode', rates)
        self.assertIn('noop_reverse', rates)
        self.assertNotIn('fill_page_meta_mode', blog)
        self.assertNotIn('fill_fiat_pair_mode', blog)
        for name in _REQUESTED[Post]:
            self.assertIn(name, blog)
        for source in (content, blog, rates):
            self.assertNotIn("name='exchange_safe'", source)
            self.assertNotIn('exchange_safe =', source)
            self.assertNotIn("['exchange_safe']", source)
        self.assertIn('fill_page_meta_mode(apps, None)', seed)
        self.assertIn('fill_fiat_pair_mode(apps, None)', seed)
