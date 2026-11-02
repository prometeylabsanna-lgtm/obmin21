from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from src.content.models import HomePage, RatesPage
from src.core.admin_city import CityQuoteInline
from src.core.models import SiteSettings
from src.core.views import _ordered_rows, _RETAIL_ORDER
from src.network.models import City
from src.rates.forms import QuoteAdminForm
from src.rates.models import QUOTE_VALUE_MAX, CurrencyPair, Quote, RateBoard
from src.rates.selectors import get_quote, get_quotes_for_city
from src.rates.services import ensure_city_quotes


class CityQuoteVisibilityTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Київ', slug='kyiv-rates', phone='+380441112233')
        self.usd = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-uah', sort_order=0)
        self.eur = CurrencyPair.objects.create(code='EUR', name='Євро', slug='eur-uah', sort_order=1)
        self.pln = CurrencyPair.objects.create(code='PLN', name='Злотий', slug='pln-uah', sort_order=2)
        self.cross = CurrencyPair.objects.create(
            code='EURUSD', name='Євро/долар', slug='eurusd', sort_order=3,
        )
        self.gbp = CurrencyPair.objects.create(code='GBP', name='Фунт', slug='gbp-uah', sort_order=4)
        for pair, buy, sell in (
            (self.usd, '41.20', '41.65'),
            (self.eur, '44.93', '45.30'),
            (self.pln, '52.10', '52.90'),
            (self.cross, '10.25', '10.62'),
            (self.gbp, '48.00', '49.00'),
        ):
            Quote.objects.create(
                pair=pair,
                board=RateBoard.RETAIL,
                city=None,
                buy=Decimal(buy),
                sell=Decimal(sell),
            )
            Quote.objects.create(
                pair=pair,
                board=RateBoard.RETAIL,
                city=self.city,
                buy=Decimal(buy),
                sell=Decimal(sell),
                is_active=pair in {self.usd, self.eur, self.cross},
            )

    def test_eurusd_flag_code_is_cross_pair(self):
        self.assertEqual(self.cross.flag_code, 'EURUSD')
        slash = CurrencyPair(code='EUR/USD')
        self.assertEqual(slash.flag_code, 'EURUSD')
        self.assertEqual(self.eur.flag_code, 'EUR')

    def test_inactive_city_quote_hides_pair(self):
        rows, _ = get_quotes_for_city(self.city, RateBoard.RETAIL)
        codes = [row['pair'].code for row in rows]
        self.assertEqual(codes, ['USD', 'EUR', 'EURUSD'])
        self.assertIsNone(get_quote(self.pln, self.city, RateBoard.RETAIL))
        self.assertIsNone(get_quote(self.gbp, self.city, RateBoard.RETAIL))
        self.assertEqual(get_quote(self.cross, self.city, RateBoard.RETAIL).buy, Decimal('10.25'))

    def test_global_quote_used_only_without_city_row(self):
        Quote.objects.filter(pair=self.gbp, city=self.city).delete()
        quote = get_quote(self.gbp, self.city, RateBoard.RETAIL)
        self.assertIsNotNone(quote)
        self.assertIsNone(quote.city_id)

    def test_ensure_city_quotes_keeps_inactive(self):
        created = ensure_city_quotes(self.city)
        self.assertEqual(created, 0)
        self.assertFalse(
            Quote.objects.get(pair=self.pln, city=self.city, board=RateBoard.RETAIL).is_active
        )

    def test_home_compact_order_prefers_eurusd_over_pln(self):
        rows, _ = get_quotes_for_city(self.city, RateBoard.RETAIL)
        ordered = _ordered_rows(rows, _RETAIL_ORDER)
        self.assertEqual([row['pair'].code for row in ordered[:3]], ['USD', 'EUR', 'EURUSD'])

    def test_duplicate_city_quote_clean(self):
        other = Quote(
            pair=self.usd,
            board=RateBoard.RETAIL,
            city=self.city,
            buy=Decimal('41.00'),
            sell=Decimal('41.10'),
        )
        with self.assertRaises(ValidationError):
            other.full_clean()

    def test_banner_inline_locks_pair(self):
        self.assertEqual(CityQuoteInline.readonly_fields, ('pair', 'board'))
        self.assertFalse(CityQuoteInline.can_delete)


class PublicRatesRespectCityActiveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        HomePage.load()
        RatesPage.load()
        cls.city = City.objects.create(name='Київ', slug='kyiv-public-rates', phone='+380441112233')
        usd = CurrencyPair.objects.create(code='USD', name='Долар', slug='usd-pub', sort_order=0)
        pln = CurrencyPair.objects.create(code='PLN', name='Злотий', slug='pln-pub', sort_order=1)
        cross = CurrencyPair.objects.create(code='EURUSD', name='Євро/долар', slug='eurusd-pub', sort_order=2)
        for pair, buy, sell, city_active in (
            (usd, '41.20', '41.65', True),
            (pln, '52.10', '52.90', False),
            (cross, '10.25', '10.62', True),
        ):
            Quote.objects.create(
                pair=pair, board=RateBoard.RETAIL, city=None,
                buy=Decimal(buy), sell=Decimal(sell),
            )
            Quote.objects.create(
                pair=pair, board=RateBoard.RETAIL, city=cls.city,
                buy=Decimal(buy), sell=Decimal(sell), is_active=city_active,
            )

    def test_pages_hide_inactive_city_quote(self):
        self.client.post(reverse('network:set_city'), {'city': self.city.slug})
        home = self.client.get(reverse('core:home'))
        kursy = self.client.get(reverse('rates:rates_page'))
        self.assertContains(home, 'EURUSD')
        self.assertContains(kursy, 'EURUSD')
        self.assertNotContains(home, 'PLN/UAH')
        self.assertNotContains(kursy, 'PLN/UAH')
        self.assertNotContains(home, 'data-code="PLN"')
        self.assertNotContains(kursy, 'data-code="PLN"')


class QuoteValueValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pair = CurrencyPair.objects.create(
            code='USD', name='Долар', slug='usd-quote-val', sort_order=0,
        )
        cls.user = User.objects.create_superuser(
            username='quote-admin',
            email='quote@example.com',
            password='pass-12345',
        )

    def _quote(self, buy, sell, **extra):
        return Quote(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal(buy),
            sell=Decimal(sell),
            **extra,
        )

    def test_rejects_non_positive_and_buy_gt_sell(self):
        over = str(QUOTE_VALUE_MAX + Decimal('0.0001'))
        cases = (
            ('-5', '41', 'buy'),
            ('0', '41', 'buy'),
            ('41', '0', 'sell'),
            ('41.50', '41.00', 'buy'),
            (over, over, 'buy'),
            ('1', over, 'sell'),
        )
        for buy, sell, field in cases:
            with self.subTest(buy=buy, sell=sell):
                quote = self._quote(buy, sell)
                with self.assertRaises(ValidationError) as ctx:
                    quote.full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_accepts_equal_bounds(self):
        quote = self._quote('41.20', '41.20')
        quote.full_clean()
        top = self._quote(str(QUOTE_VALUE_MAX), str(QUOTE_VALUE_MAX))
        top.full_clean()
        field = Quote._meta.get_field('buy')
        integer_digits = field.max_digits - field.decimal_places
        self.assertLess(QUOTE_VALUE_MAX, Decimal(10) ** integer_digits)

    def test_btc_uah_2450000_is_valid(self):
        pair = CurrencyPair.objects.create(
            code='BTC/UAH',
            name='Біткоїн',
            slug='btc-uah-prod',
            base_code='UAH',
            sort_order=9,
        )
        quote = Quote(
            pair=pair,
            board=RateBoard.CRYPTO,
            city=None,
            buy=Decimal('2450000'),
            sell=Decimal('2450000'),
        )
        quote.full_clean()
        quote.save()
        stored = Quote.objects.get(pk=quote.pk)
        self.assertEqual(stored.buy, Decimal('2450000'))
        self.assertEqual(stored.sell, Decimal('2450000'))

    def test_admin_form_and_inline_use_validation(self):
        form = QuoteAdminForm(data={
            'pair': self.pair.pk,
            'board': RateBoard.RETAIL,
            'city': '',
            'buy': '-5',
            'sell': '41',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('buy', form.errors)
        self.assertIn('більшою за 0', form.errors['buy'][0])
        self.assertIs(CityQuoteInline.form, QuoteAdminForm)

    def test_admin_change_rejects_buy_gt_sell(self):
        quote = self._quote('41.20', '41.65')
        quote.save()
        client = Client()
        client.force_login(self.user)
        url = reverse('admin:rates_quote_change', args=[quote.pk])
        response = client.post(url, {
            'pair': self.pair.pk,
            'city': '',
            'buy': '50',
            'sell': '40',
            'is_active': 'on',
            'board': RateBoard.RETAIL,
        })
        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        self.assertEqual(quote.buy, Decimal('41.20'))
        self.assertEqual(quote.sell, Decimal('41.65'))
