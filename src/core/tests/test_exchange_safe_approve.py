import importlib

from django.apps import apps
from django.contrib import admin
from django.test import TestCase

from src.blog.models import Category, Post
from src.content.models import Service
from src.core.exchange_fields import EXCHANGE_SAFE_CURRENCY_HELP
from src.core.exchange_safe_approve import (
    APPROVED_PAIR_SLUGS,
    APPROVED_POST_IDS,
    APPROVED_REVIEW_IDS,
    clear_approved_exchange_safe,
    mark_approved_exchange_safe,
)
from src.rates.models import CurrencyPair
from src.reviews.models import Review

_MISSING_POST_ID = 17
_MISSING_REVIEW_ID = 10
_MISSING_PAIR_SLUG = 'mdl-uah'
_KEPT_TRUE_POST_ID = 6
_KEPT_TRUE_REVIEW_ID = 7
_KEPT_TRUE_PAIR = 'kzt-uah'
_UNCHANGED_PAIRS = (
    'btc-uah',
    'btc-usdt',
    'eth-uah',
    'eth-usdt',
    'usdt-uah',
    'usdt-eur',
    'gold-uah',
    'xau-gold',
    'eur-usd',
    'aud-uah',
)
_OTHER_POST_IDS = (1, 9, 11, 13, 16)
_OTHER_REVIEW_IDS = (6, 9, 11)


def _flags(model, attr='pk'):
    return dict(model.objects.order_by('pk').values_list(attr, 'exchange_safe'))


class ApprovedExchangeSafeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Журнал', slug='zhurnal-approve')

    def _posts(self):
        present = [pk for pk in APPROVED_POST_IDS if pk != _MISSING_POST_ID]
        for pk in present:
            Post.objects.create(
                pk=pk,
                category=self.category,
                title=f'Стаття {pk}',
                slug=f'stattya-{pk}',
                body='Текст',
                exchange_safe=(pk == 2),
            )
        for pk in _OTHER_POST_IDS:
            Post.objects.create(
                pk=pk,
                category=self.category,
                title=f'Інша {pk}',
                slug=f'insha-{pk}',
                body='Текст',
                exchange_safe=False,
            )
        Post.objects.create(
            pk=_KEPT_TRUE_POST_ID,
            category=self.category,
            title='Залишити',
            slug='zalyshyty',
            body='Текст',
            exchange_safe=True,
        )

    def _reviews(self):
        present = [pk for pk in APPROVED_REVIEW_IDS if pk != _MISSING_REVIEW_ID]
        for pk in present:
            Review.objects.create(
                pk=pk,
                name=f'Імʼя {pk}',
                text='Добре',
                exchange_safe=False,
            )
        for pk in _OTHER_REVIEW_IDS:
            Review.objects.create(
                pk=pk,
                name=f'Інший {pk}',
                text='Добре',
                exchange_safe=False,
            )
        Review.objects.create(
            pk=_KEPT_TRUE_REVIEW_ID,
            name='Залишити',
            text='Добре',
            exchange_safe=True,
        )

    def _pairs(self):
        present = [slug for slug in APPROVED_PAIR_SLUGS if slug != _MISSING_PAIR_SLUG]
        for slug in present:
            CurrencyPair.objects.create(
                code=slug[:3].upper(),
                name=slug,
                slug=slug,
                exchange_safe=(slug == 'usd-uah'),
            )
        for slug in _UNCHANGED_PAIRS:
            CurrencyPair.objects.create(
                code=slug[:8].upper(),
                name=slug,
                slug=slug,
                exchange_safe=False,
            )
        CurrencyPair.objects.create(
            code='KZT',
            name='Тенге',
            slug=_KEPT_TRUE_PAIR,
            exchange_safe=True,
        )

    def test_post_and_review_forms_use_currency_help(self):
        for model in (Post, Review):
            field = model._meta.get_field('exchange_safe')
            self.assertEqual(field.help_text, EXCHANGE_SAFE_CURRENCY_HELP)
            self.assertIs(field.default, False)
            model_admin = admin.site._registry[model]
            names = []
            for _title, opts in model_admin.fieldsets:
                names.extend(opts['fields'])
            self.assertIn('exchange_safe', names)
            self.assertEqual(names[0], 'exchange_safe')

    def test_migration_marks_listed_skips_missing_and_reverse_clears_only_them(self):
        self._posts()
        self._reviews()
        self._pairs()
        kept_service = Service.objects.create(
            title='Залишена послуга',
            slug='zalyshena-posluha',
            short_desc='Текст',
            exchange_safe=True,
        )
        plain_service = Service.objects.create(
            title='Звичайна послуга',
            slug='zvychaina-posluha',
            short_desc='Текст',
            exchange_safe=False,
        )
        before_services = _flags(Service)
        self.assertFalse(Post.objects.filter(pk=_MISSING_POST_ID).exists())
        self.assertFalse(Review.objects.filter(pk=_MISSING_REVIEW_ID).exists())
        self.assertFalse(CurrencyPair.objects.filter(slug=_MISSING_PAIR_SLUG).exists())
        post_titles = dict(Post.objects.values_list('pk', 'title'))
        counts = (
            Post.objects.count(),
            Review.objects.count(),
            CurrencyPair.objects.count(),
        )

        mark_approved_exchange_safe(apps, None)
        mark_approved_exchange_safe(apps, None)

        present_posts = {
            pk for pk in APPROVED_POST_IDS if pk != _MISSING_POST_ID
        }
        present_reviews = {
            pk for pk in APPROVED_REVIEW_IDS if pk != _MISSING_REVIEW_ID
        }
        present_pairs = {
            slug for slug in APPROVED_PAIR_SLUGS if slug != _MISSING_PAIR_SLUG
        }
        posts = _flags(Post)
        reviews = _flags(Review)
        pairs = _flags(CurrencyPair, 'slug')
        self.assertEqual(
            {pk for pk, safe in posts.items() if safe},
            present_posts | {_KEPT_TRUE_POST_ID},
        )
        self.assertEqual(
            {pk for pk, safe in reviews.items() if safe},
            present_reviews | {_KEPT_TRUE_REVIEW_ID},
        )
        self.assertEqual(
            {slug for slug, safe in pairs.items() if safe},
            present_pairs | {_KEPT_TRUE_PAIR},
        )
        for slug in _UNCHANGED_PAIRS:
            self.assertFalse(pairs[slug], slug)
        self.assertNotIn(_MISSING_PAIR_SLUG, pairs)
        self.assertEqual(_flags(Service), before_services)
        self.assertEqual(dict(Post.objects.values_list('pk', 'title')), post_titles)
        self.assertEqual(
            (Post.objects.count(), Review.objects.count(), CurrencyPair.objects.count()),
            counts,
        )
        self.assertFalse(Post.objects.filter(pk=_MISSING_POST_ID).exists())
        self.assertFalse(Review.objects.filter(pk=_MISSING_REVIEW_ID).exists())

        clear_approved_exchange_safe(apps, None)

        posts = _flags(Post)
        reviews = _flags(Review)
        pairs = _flags(CurrencyPair, 'slug')
        self.assertEqual({pk for pk, safe in posts.items() if safe}, {_KEPT_TRUE_POST_ID})
        self.assertEqual(
            {pk for pk, safe in reviews.items() if safe},
            {_KEPT_TRUE_REVIEW_ID},
        )
        self.assertEqual({slug for slug, safe in pairs.items() if safe}, {_KEPT_TRUE_PAIR})
        for slug in present_pairs:
            self.assertFalse(pairs[slug], slug)
        for slug in _UNCHANGED_PAIRS:
            self.assertFalse(pairs[slug], slug)
        kept_service.refresh_from_db()
        plain_service.refresh_from_db()
        self.assertTrue(kept_service.exchange_safe)
        self.assertFalse(plain_service.exchange_safe)
        self.assertFalse(Post.objects.filter(pk=_MISSING_POST_ID).exists())
        self.assertFalse(CurrencyPair.objects.filter(slug=_MISSING_PAIR_SLUG).exists())

    def test_migration_is_reversible_runpython(self):
        migration = importlib.import_module(
            'src.blog.migrations.0009_approved_exchange_safe_flags',
        )
        self.assertEqual(
            migration.Migration.dependencies,
            [
                ('blog', '0008_exchange_safe_currency_help'),
                ('rates', '0006_pair_meta_mode'),
                ('reviews', '0006_exchange_safe_currency_help'),
            ],
        )
        self.assertEqual(len(migration.Migration.operations), 1)
        operation = migration.Migration.operations[0]
        self.assertEqual(operation.code, mark_approved_exchange_safe)
        self.assertEqual(operation.reverse_code, clear_approved_exchange_safe)
