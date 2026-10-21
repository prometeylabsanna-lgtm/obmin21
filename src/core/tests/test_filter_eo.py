import importlib
import os
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from django.test import TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.bot.services import exchange_pairs, pair_by_id
from src.content.models import AdvantageItem, AdvantagesPage, FaqItem, HomePage, HomeStat, Service
from src.core.exchange_mode import raise_hidden
from src.core.exchange_stopwords import STOP_WORDS
from src.core.models import SiteSettings
from src.leads.forms import RETAIL_ONLY_BOARD_ERROR, ExchangeRequestForm
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard
from src.rates.selectors import get_active_pairs, get_quote, public_board, public_boards
from src.reviews.models import Review

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class _ModeCase(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        self._mode(False)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)


class HiddenHookTests(_ModeCase):
    def test_raise_hidden_is_404_even_if_status_is_503(self):
        SiteSettings.objects.filter(pk=1).update(hidden_page_status=503)
        with self.assertRaises(Http404):
            raise_hidden()


class PublicFilterTests(_ModeCase):
    def setUp(self):
        super().setUp()
        self.city = City.objects.create(name='Київ EO', slug='kyiv-eo', phone='+380441112233')
        self.branch = Branch.objects.create(
            city=self.city,
            address='Київ, вул. Тестова, 1',
            phone=self.city.phone,
        )
        self.usd = CurrencyPair.objects.create(
            code='USD',
            name='Долар EO',
            slug='usd-eo',
            exchange_safe=True,
        )
        self.btc = CurrencyPair.objects.create(
            code='BTC',
            name='Bitcoin EO',
            slug='btc-eo',
            exchange_safe=False,
        )
        for pair in (self.usd, self.btc):
            Quote.objects.create(
                pair=pair,
                board=RateBoard.RETAIL,
                buy=Decimal('40'),
                sell=Decimal('41'),
            )
            Quote.objects.create(
                pair=pair,
                board=RateBoard.CRYPTO,
                buy=Decimal('10'),
                sell=Decimal('11'),
            )
        self.cat_open = Category.objects.create(name='EO-CAT-OPEN', slug='eo-cat-open')
        self.cat_shut = Category.objects.create(name='EO-CAT-SHUT', slug='eo-cat-shut')
        self.cat_menu_off = Category.objects.create(
            name='EO-CAT-MENU',
            slug='eo-cat-menu',
            show_in_filter=False,
        )
        self.post_open = Post.objects.create(
            category=self.cat_open,
            title='EO-POST-OPEN',
            slug='eo-post-open',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        self.post_also = Post.objects.create(
            category=self.cat_open,
            title='EO-POST-ALSO',
            slug='eo-post-also',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        self.post_shut = Post.objects.create(
            category=self.cat_shut,
            title='EO-POST-SHUT',
            slug='eo-post-shut',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=False,
        )
        Post.objects.create(
            category=self.cat_menu_off,
            title='EO-POST-MENU',
            slug='eo-post-menu',
            body='Текст',
            status=Post.Status.PUBLISHED,
            exchange_safe=True,
        )
        self.post_open.related_posts.add(self.post_shut, self.post_also)
        self.safe_service = Service.objects.create(
            title='EO-SAFE-SVC',
            slug='eo-safe-svc',
            short_desc='Обмін',
            exchange_safe=True,
        )
        self.hidden_service = Service.objects.create(
            title='EO-HIDDEN-SVC',
            slug='eo-hidden-svc',
            short_desc='Обмін',
            exchange_safe=False,
        )
        FaqItem.objects.create(
            question='EO-FAQ-SAFE',
            answer='Відповідь',
            exchange_safe=True,
        )
        FaqItem.objects.create(
            question='EO-FAQ-HIDDEN',
            answer='Відповідь',
            exchange_safe=False,
        )
        AdvantageItem.objects.create(
            audience=AdvantageItem.Audience.CITIZENS,
            text='EO-ADV-SAFE',
            exchange_safe=True,
        )
        AdvantageItem.objects.create(
            audience=AdvantageItem.Audience.CITIZENS,
            text='EO-ADV-HIDDEN',
            exchange_safe=False,
        )
        Review.objects.create(name='Олена', text='EO-REVIEW-SAFE', is_published=True, exchange_safe=True)
        Review.objects.create(name='Ігор', text='EO-REVIEW-HIDDEN', is_published=True, exchange_safe=False)
        page = HomePage.load()
        HomeStat.objects.create(
            page=page,
            number='1',
            text='EO-STAT-SAFE',
            exchange_safe=True,
            is_active=True,
        )
        HomeStat.objects.create(
            page=page,
            number='2',
            text='EO-STAT-HIDDEN',
            exchange_safe=False,
            is_active=True,
        )
        HomeStat.objects.create(
            page=page,
            number='3',
            text='EO-STAT-OFF',
            exchange_safe=True,
            is_active=False,
        )

    def _codes(self, response):
        return [row['pair'].code for row in response.context['rate_rows']]

    def test_pairs_boards_and_quotes_follow_visible(self):
        self._mode(False)
        self.assertEqual(public_board('crypto'), RateBoard.CRYPTO)
        self.assertIn(RateBoard.CRYPTO, [item[0] for item in public_boards()])
        self.assertIn(self.btc.pk, set(get_active_pairs().values_list('pk', flat=True)))
        self.assertIsNotNone(get_quote(self.btc, self.city, RateBoard.RETAIL))

        self._mode(True)
        self.assertEqual(public_board('crypto'), RateBoard.RETAIL)
        self.assertNotIn(RateBoard.CRYPTO, [item[0] for item in public_boards()])
        visible_ids = set(get_active_pairs().values_list('pk', flat=True))
        self.assertIn(self.usd.pk, visible_ids)
        self.assertNotIn(self.btc.pk, visible_ids)
        self.assertIsNone(get_quote(self.btc, self.city, RateBoard.RETAIL))

        rates = self.client.get(reverse('rates:rates_page') + '?board=crypto')
        self.assertEqual(rates.context['active_board'], RateBoard.RETAIL)
        self.assertNotIn(RateBoard.CRYPTO, [item[0] for item in rates.context['boards']])
        self.assertIn('USD', self._codes(rates))
        self.assertNotIn('BTC', self._codes(rates))

        partial = self.client.get(reverse('core:rates_partial') + '?board=crypto')
        self.assertEqual(partial.context['active_board'], RateBoard.RETAIL)
        self.assertNotIn('BTC', self._codes(partial))

        payload = self.client.get(reverse('core:quotes_json') + '?board=crypto').json()
        codes = [item['code'] for item in payload['quotes']]
        self.assertIn('USD', codes)
        self.assertNotIn('BTC', codes)

    def test_hidden_pair_and_post_use_raise_hidden(self):
        self._mode(True)
        with patch('src.rates.views.raise_hidden', side_effect=Http404) as hook:
            missing = self.client.get(reverse('rates:pair_detail', kwargs={'slug': 'nema-eo'}))
            self.assertEqual(missing.status_code, 404)
            hook.assert_not_called()
            hidden = self.client.get(reverse('rates:pair_detail', kwargs={'slug': self.btc.slug}))
            self.assertEqual(hidden.status_code, 404)
            hook.assert_called_once()
        shown = self.client.get(reverse('rates:pair_detail', kwargs={'slug': self.usd.slug}))
        self.assertEqual(shown.status_code, 200)
        self.assertContains(shown, 'Долар EO')

        with patch('src.blog.views.raise_hidden', side_effect=Http404) as hook:
            missing_post = self.client.get(reverse('blog:post_detail', kwargs={'slug': 'nema-post-eo'}))
            self.assertEqual(missing_post.status_code, 404)
            hook.assert_not_called()
            hidden_post = self.client.get(
                reverse('blog:post_detail', kwargs={'slug': self.post_shut.slug}),
            )
            self.assertEqual(hidden_post.status_code, 404)
            hook.assert_called_once()
            hidden_cat = self.client.get(
                reverse('blog:category', kwargs={'category_slug': self.cat_shut.slug}),
            )
            self.assertEqual(hidden_cat.status_code, 404)
            self.assertEqual(hook.call_count, 2)

        menu_off = self.client.get(
            reverse('blog:category', kwargs={'category_slug': self.cat_menu_off.slug}),
        )
        self.assertEqual(menu_off.status_code, 404)

        detail = self.client.get(reverse('blog:post_detail', kwargs={'slug': self.post_open.slug}))
        self.assertContains(detail, 'EO-POST-ALSO')
        self.assertNotContains(detail, 'EO-POST-SHUT')

        blog = self.client.get(reverse('blog:post_list'))
        self.assertContains(blog, 'EO-CAT-OPEN')
        self.assertContains(blog, 'EO-POST-OPEN')
        self.assertNotContains(blog, 'EO-CAT-SHUT')
        self.assertNotContains(blog, 'EO-POST-SHUT')

        self._mode(False)
        self.assertEqual(
            self.client.get(reverse('rates:pair_detail', kwargs={'slug': self.btc.slug})).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse('blog:category', kwargs={'category_slug': self.cat_shut.slug}),
            ).status_code,
            200,
        )
        blog_off = self.client.get(reverse('blog:post_list'))
        self.assertContains(blog_off, 'EO-CAT-SHUT')
        self.assertContains(blog_off, 'EO-POST-SHUT')

    def test_services_faq_reviews_stats_and_footer(self):
        self._mode(True)
        services = self.client.get(reverse('content:services'))
        self.assertContains(services, 'EO-SAFE-SVC')
        self.assertNotContains(services, 'EO-HIDDEN-SVC')
        footer = [item.title for item in services.context['footer_services']]
        self.assertIn('EO-SAFE-SVC', footer)
        self.assertNotIn('EO-HIDDEN-SVC', footer)

        faq = self.client.get(reverse('content:faq'))
        questions = [item.question for item in faq.context['faq_items']]
        self.assertIn('EO-FAQ-SAFE', questions)
        self.assertNotIn('EO-FAQ-HIDDEN', questions)

        advantages = self.client.get(reverse('content:advantages'))
        texts = [item.text for item in advantages.context['items']]
        self.assertIn('EO-ADV-SAFE', texts)
        self.assertNotIn('EO-ADV-HIDDEN', texts)

        reviews = self.client.get(reverse('reviews:review_list'))
        self.assertContains(reviews, 'EO-REVIEW-SAFE')
        self.assertNotContains(reviews, 'EO-REVIEW-HIDDEN')

        home = self.client.get(reverse('core:home'))
        self.assertContains(home, 'EO-STAT-SAFE')
        self.assertNotContains(home, 'EO-STAT-HIDDEN')
        self.assertNotContains(home, 'EO-STAT-OFF')
        self.assertContains(home, 'EO-SAFE-SVC')
        self.assertNotContains(home, 'EO-HIDDEN-SVC')
        self.assertContains(home, 'EO-POST-OPEN')
        self.assertNotContains(home, 'EO-POST-SHUT')

    def test_sitemap_uses_visible_posts_and_pairs(self):
        self._mode(True)
        hidden = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('eo-post-open', hidden)
        self.assertNotIn('eo-post-shut', hidden)
        self.assertIn('usd-eo', hidden)
        self.assertNotIn('btc-eo', hidden)
        self._mode(False)
        shown = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('eo-post-shut', shown)
        self.assertIn('btc-eo', shown)

    def test_form_rejects_crypto_board_and_hidden_pair(self):
        self._mode(True)
        crypto = self._form(self.usd, RateBoard.CRYPTO)
        self.assertFalse(crypto.is_valid())
        self.assertIn(RETAIL_ONLY_BOARD_ERROR, crypto.errors['board'])
        hidden_pair = self._form(self.btc, RateBoard.RETAIL)
        self.assertFalse(hidden_pair.is_valid())
        self.assertIn('pair', hidden_pair.errors)
        retail = self._form(self.usd, RateBoard.RETAIL)
        self.assertTrue(retail.is_valid(), retail.errors)

        self._mode(False)
        opened = self._form(self.btc, RateBoard.CRYPTO)
        self.assertTrue(opened.is_valid(), opened.errors)

    def _form(self, pair, board):
        return ExchangeRequestForm(data={
            'name': 'Олег',
            'phone': '+380991234567',
            'pair': pair.pk,
            'board': board,
            'direction': 'sell',
            'amount_give': '100',
            'branch': self.branch.pk,
            'consent': True,
        }, city=self.city)

    def test_bot_pairs_use_visible(self):
        self._mode(True)
        self.assertIsNone(pair_by_id(self.btc.pk))
        self.assertEqual(pair_by_id(self.usd.pk).pk, self.usd.pk)
        ids = {pair.pk for pair in exchange_pairs()}
        self.assertIn(self.usd.pk, ids)
        self.assertNotIn(self.btc.pk, ids)
        self._mode(False)
        self.assertEqual(pair_by_id(self.btc.pk).pk, self.btc.pk)


class QuoteOrderTests(_ModeCase):
    def test_crypto_board_orders_btc_eth_usdt_first(self):
        specs = (
            ('USDT', 'usdt-sort', 0),
            ('XRP', 'xrp-sort', 1),
            ('ETH', 'eth-sort', 2),
            ('BTC', 'btc-sort', 3),
        )
        for code, slug, order in specs:
            pair = CurrencyPair.objects.create(
                code=code,
                name=code,
                slug=slug,
                sort_order=order,
                exchange_safe=True,
            )
            Quote.objects.create(
                pair=pair,
                board=RateBoard.CRYPTO,
                buy=Decimal('2'),
                sell=Decimal('3'),
            )
        self._mode(False)
        payload = self.client.get(reverse('core:quotes_json') + '?board=crypto').json()
        codes = [item['code'] for item in payload['quotes']]
        self.assertEqual(codes, ['BTC', 'ETH', 'USDT', 'XRP'])
        partial = self.client.get(reverse('core:rates_partial') + '?board=crypto')
        row_codes = [row['pair'].flag_code for row in partial.context['rate_rows']]
        self.assertEqual(row_codes, ['BTC', 'ETH', 'USDT', 'XRP'])


class ParserRemovedTests(_ModeCase):
    def test_stopwords_kept_and_parser_is_gone(self):
        self.assertIn('крипт', STOP_WORDS)
        self.assertIn('btc', STOP_WORDS)
        self.assertIn('swift', STOP_WORDS)
        self.assertIn('електронн валют', STOP_WORDS)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module('src.core.crypto_visibility')

    def test_crypto_text_filters_removed_and_stats_keep_wording(self):
        module = importlib.import_module('src.core.templatetags.content_format')
        self.assertFalse(hasattr(module, 'strip_crypto_items'))
        self.assertFalse(hasattr(module, 'hide_if_crypto'))
        self.assertNotIn('strip_crypto_items', module.register.filters)
        self.assertNotIn('hide_if_crypto', module.register.filters)
        blob = ' '.join(row['text'] for row in AdvantagesPage.load().iter_stats())
        self.assertIn('криптоактивів', blob)

    def test_booking_script_has_no_hardcoded_crypto_symbols(self):
        script = (settings.BASE_DIR / 'src/core/static/js/booking-modal.js').read_text(encoding='utf-8')
        for token in ('USDT', 'BTC', 'ETH'):
            self.assertNotIn(token, script)
        self.assertIn('item.symbol', script)
