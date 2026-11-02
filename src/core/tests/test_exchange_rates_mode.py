import os
from decimal import Decimal

from django.apps import apps
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import AdvantageItem, HomePage, RatesPage, Service
from src.core.exchange_classify import (
    assign_pair_exchange_fields,
    assign_post_exchange_fields,
    assign_service_exchange_fields,
    assign_visibility_from_exchange_safe,
    classify_pair_kind,
    resolved_content_kind,
)
from src.core.exchange_mode import ExchangeVisibility
from src.core.models import SiteSettings
from src.rates.models import CurrencyPair, Quote, RateBoard

_ENV = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')


class ClassifyTests(TestCase):
    def test_pair_and_content_kinds(self):
        self.assertEqual(classify_pair_kind('USD/UAH', 'Долар', 'usd-uah'), 'fiat')
        self.assertEqual(classify_pair_kind('EURUSD', 'Євро/долар', 'eur-usd'), 'fiat')
        self.assertEqual(classify_pair_kind('BTC/USDT', 'Bitcoin', 'btc-usdt'), 'crypto')
        self.assertEqual(classify_pair_kind('USDT', 'Tether', 'usdt'), 'crypto')
        self.assertEqual(classify_pair_kind('XAU', 'Золото', 'xau'), 'metal')
        self.assertEqual(classify_pair_kind('USD', 'SWIFT переказ', 'swift'), 'other')
        self.assertEqual(
            resolved_content_kind('Курс долара', 'kurs-dolara', 'Валюта'),
            'currency',
        )
        self.assertEqual(
            resolved_content_kind('Криптовалюта BTC', 'krypto', 'Біткоїн'),
            'non_exchange',
        )
        self.assertEqual(
            resolved_content_kind('Інвестиційне золото', 'zoloto'),
            'non_exchange',
        )
        self.assertEqual(
            resolved_content_kind('Міжнародні перекази', 'swift'),
            'non_exchange',
        )
        self.assertEqual(resolved_content_kind('Окрема нотатка', 'notatka'), 'non_exchange')


class ExchangeRatesModeTests(TestCase):
    def setUp(self):
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        HomePage.load()
        RatesPage.load()
        self.category = Category.objects.create(name='Валюта', slug='valyuta-mode')
        self.usd = self._pair('USD/UAH', 'Долар', 'usd-uah-mode')
        self.eur = self._pair('EUR/UAH', 'Євро', 'eur-uah-mode')
        self.btc = self._pair('BTC/USDT', 'Bitcoin', 'btc-mode')
        self.gold = self._pair('XAU', 'Золото', 'xau-mode')
        self.swift = self._pair('USD', 'SWIFT переказ', 'swift-mode')
        for pair in (self.usd, self.eur, self.btc, self.gold, self.swift):
            Quote.objects.create(
                pair=pair,
                board=RateBoard.RETAIL,
                buy=Decimal('40'),
                sell=Decimal('41'),
            )
        self.dollar_post = self._post('Курс долара', 'kurs-dolara-mode')
        self.crypto_post = self._post('Криптовалюта і біткоїн', 'krypto-mode')
        self.gold_post = self._post('Інвестиційне золото', 'zoloto-mode')
        self.swift_post = self._post('Міжнародні перекази SWIFT', 'perekaz-mode')

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _pair(self, code, name, slug):
        return CurrencyPair.objects.create(code=code, name=name, slug=slug, is_active=True)

    def _post(self, title, slug):
        return Post.objects.create(
            category=self.category,
            title=title,
            slug=slug,
            body='Текст',
            status=Post.Status.PUBLISHED,
        )

    def _mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def _codes(self, response):
        return [row['pair'].code for row in response.context['rate_rows']]

    def _pair_urls(self):
        return [
            reverse('rates:pair_detail', args=[pair.slug])
            for pair in (self.usd, self.eur, self.btc, self.gold, self.swift)
        ]

    def _post_urls(self):
        return [
            reverse('blog:post_detail', args=[post.slug])
            for post in (
                self.dollar_post, self.crypto_post, self.gold_post, self.swift_post,
            )
        ]

    def test_fiat_pages_and_rates_stay_open_crypto_metal_swift_hide(self):
        self._mode(False)
        for url in self._pair_urls() + self._post_urls():
            self.assertEqual(self.client.get(url).status_code, 200, url)

        self._mode(True)
        self.assertEqual(self.client.get(reverse('rates:pair_detail', args=[self.usd.slug])).status_code, 200)
        self.assertEqual(self.client.get(reverse('rates:pair_detail', args=[self.eur.slug])).status_code, 200)
        for pair in (self.btc, self.gold, self.swift):
            hidden = self.client.get(reverse('rates:pair_detail', args=[pair.slug]))
            self.assertEqual(hidden.status_code, 503, pair.slug)
        self.assertEqual(
            self.client.get(reverse('blog:post_detail', args=[self.dollar_post.slug])).status_code,
            200,
        )
        for post in (self.crypto_post, self.gold_post, self.swift_post):
            hidden = self.client.get(reverse('blog:post_detail', args=[post.slug]))
            self.assertEqual(hidden.status_code, 503, post.slug)

        for url_name in ('core:home', 'rates:rates_page'):
            page = self.client.get(reverse(url_name))
            self.assertEqual(page.status_code, 200, url_name)
            codes = self._codes(page)
            self.assertIn('USD/UAH', codes)
            self.assertIn('EUR/UAH', codes)
            self.assertNotIn('BTC/USDT', codes)
            self.assertNotIn('XAU', codes)

    def test_manual_show_and_hide_win(self):
        self.btc.exchange_visibility = ExchangeVisibility.SHOW
        self.btc.exchange_safe = False
        self.btc.save(update_fields=['exchange_visibility', 'exchange_safe'])
        self.usd.exchange_visibility = ExchangeVisibility.HIDE
        self.usd.save(update_fields=['exchange_visibility'])
        self._mode(True)
        self.assertEqual(
            self.client.get(reverse('rates:pair_detail', args=[self.btc.slug])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('rates:pair_detail', args=[self.usd.slug])).status_code,
            503,
        )

    def test_data_migration_classifies_existing_rows(self):
        pair = CurrencyPair.objects.create(code='PLN', name='Злотий', slug='pln-mig')
        CurrencyPair.objects.filter(pk=pair.pk).update(
            kind='other',
            exchange_safe=True,
            exchange_visibility='auto',
        )
        post = self._post('Курс євро', 'ievro-mig')
        Post.objects.filter(pk=post.pk).update(
            content_kind='non_exchange',
            exchange_safe=False,
            exchange_visibility='hide',
        )
        service = Service.objects.create(
            title='Обмін долара',
            slug='dolar-mig',
            short_desc='Каса',
            exchange_safe=True,
        )
        Service.objects.filter(pk=service.pk).update(
            content_kind='auto',
            exchange_visibility='auto',
        )
        stat = AdvantageItem.objects.create(
            audience=AdvantageItem.Audience.CITIZENS,
            text='Пункт міграції',
            exchange_safe=True,
        )
        AdvantageItem.objects.filter(pk=stat.pk).update(exchange_visibility='auto')

        assign_pair_exchange_fields(apps, None)
        assign_post_exchange_fields(apps, None)
        assign_service_exchange_fields(apps, None)
        assign_visibility_from_exchange_safe(apps, None, (('content', 'AdvantageItem'),))

        pair.refresh_from_db()
        post.refresh_from_db()
        service.refresh_from_db()
        stat.refresh_from_db()
        self.assertEqual(pair.kind, 'fiat')
        self.assertEqual(pair.exchange_visibility, 'show')
        self.assertEqual(post.content_kind, 'currency')
        self.assertEqual(post.exchange_visibility, 'auto')
        self.assertEqual(service.content_kind, 'currency')
        self.assertEqual(service.exchange_visibility, 'show')
        self.assertEqual(stat.exchange_visibility, 'show')
