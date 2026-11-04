from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from src.network.models import City
from src.rates.base_rate import assign_inherits_base
from src.rates.models import CurrencyPair, Quote, RateBoard
from src.rates.selectors import get_quote, get_quotes_for_city


class BaseQuoteTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Львів', slug='lviv-base')
        self.pair = CurrencyPair.objects.create(
            code='USD',
            name='Долар',
            slug='usd-base',
            sort_order=0,
        )
        self.base = Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('40.00'),
            sell=Decimal('41.00'),
        )

    def _city_quote(self, buy='40.00', sell='41.00', active=True):
        return Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=self.city,
            buy=Decimal(buy),
            sell=Decimal(sell),
            is_active=active,
        )

    def test_new_match_inherits_and_base_edit_reaches_city(self):
        city_quote = self._city_quote()
        self.assertTrue(city_quote.inherits_base)
        self.base.buy = Decimal('42.50')
        self.base.sell = Decimal('43.00')
        self.base.save()
        shown = get_quote(self.pair, self.city, RateBoard.RETAIL)
        self.assertEqual(shown.buy, Decimal('42.50'))
        city_quote.refresh_from_db()
        self.assertEqual(city_quote.buy, Decimal('40.00'))
        rows, _updated = get_quotes_for_city(self.city, RateBoard.RETAIL)
        self.assertEqual(rows[0]['quote'].buy, Decimal('42.50'))

    def test_different_rates_stay_override(self):
        city_quote = self._city_quote(buy='39.00', sell='39.50')
        self.assertFalse(city_quote.inherits_base)
        self.base.buy = Decimal('42.50')
        self.base.sell = Decimal('43.00')
        self.base.save()
        shown = get_quote(self.pair, self.city, RateBoard.RETAIL)
        self.assertEqual(shown.buy, Decimal('39.00'))

    def test_inactive_city_row_hides_even_when_numbers_match(self):
        city_quote = self._city_quote(active=False)
        self.assertFalse(city_quote.inherits_base)
        self.assertIsNone(get_quote(self.pair, self.city, RateBoard.RETAIL))
        rows, _updated = get_quotes_for_city(self.city, RateBoard.RETAIL)
        self.assertEqual(rows, [])

    def test_missing_city_row_uses_base(self):
        shown = get_quote(self.pair, self.city, RateBoard.RETAIL)
        self.assertEqual(shown.buy, Decimal('40.00'))
        self.assertIsNone(shown.city_id)

    def test_explicit_inherit_keeps_flag_when_numbers_differ(self):
        city_quote = self._city_quote(buy='39.00', sell='39.50')
        city_quote.inherits_base = True
        city_quote.save()
        city_quote.refresh_from_db()
        self.assertTrue(city_quote.inherits_base)
        self.assertEqual(city_quote.buy, Decimal('39.00'))
        self.assertEqual(get_quote(self.pair, self.city, RateBoard.RETAIL).sell, Decimal('41.00'))

    def test_data_migration_matches_rates_and_activity(self):
        same = self._city_quote()
        other_city = City.objects.create(name='Одеса', slug='odesa-base')
        different = Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=other_city,
            buy=Decimal('10.00'),
            sell=Decimal('11.00'),
        )
        quiet = City.objects.create(name='Дніпро', slug='dnipro-base')
        inactive = Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=quiet,
            buy=Decimal('40.00'),
            sell=Decimal('41.00'),
            is_active=False,
        )
        Quote.objects.filter(pk__in=[same.pk, different.pk, inactive.pk]).update(inherits_base=False)
        assign_inherits_base(apps, None)
        same.refresh_from_db()
        different.refresh_from_db()
        inactive.refresh_from_db()
        self.assertTrue(same.inherits_base)
        self.assertFalse(different.inherits_base)
        self.assertFalse(inactive.inherits_base)
        self.assertEqual(get_quote(self.pair, self.city, RateBoard.RETAIL).buy, Decimal('40.00'))


class QuoteInheritAdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username='rate-admin',
            email='rate@example.com',
            password='pass-12345',
        )
        self.client.force_login(user)
        self.city = City.objects.create(name='Харків', slug='kharkiv-base')
        self.pair = CurrencyPair.objects.create(
            code='EUR',
            name='Євро',
            slug='eur-base',
            sort_order=1,
        )
        self.base = Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=None,
            buy=Decimal('44.00'),
            sell=Decimal('45.00'),
        )
        self.city_quote = Quote.objects.create(
            pair=self.pair,
            board=RateBoard.RETAIL,
            city=self.city,
            buy=Decimal('43.00'),
            sell=Decimal('44.00'),
        )
        self.url = reverse('admin:rates_quote_changelist')

    def test_reset_waits_for_confirm_then_follows_base(self):
        preview = self.client.post(self.url, {
            'action': 'reset_to_base_rate',
            '_selected_action': [str(self.city_quote.pk)],
        })
        self.assertContains(preview, 'Скинути до базового курсу')
        self.city_quote.refresh_from_db()
        self.assertFalse(self.city_quote.inherits_base)
        done = self.client.post(self.url, {
            'action': 'reset_to_base_rate',
            '_selected_action': [str(self.city_quote.pk)],
            'confirm': 'yes',
        }, follow=True)
        self.assertContains(done, 'Скинуто до базового курсу: 1.')
        self.city_quote.refresh_from_db()
        self.assertTrue(self.city_quote.inherits_base)
        self.assertEqual(self.city_quote.buy, Decimal('43.00'))
        self.assertEqual(get_quote(self.pair, self.city, RateBoard.RETAIL).buy, Decimal('44.00'))
        self.base.buy = Decimal('46.00')
        self.base.sell = Decimal('47.00')
        self.base.save()
        self.assertEqual(get_quote(self.pair, self.city, RateBoard.RETAIL).buy, Decimal('46.00'))

    def test_override_snapshots_effective_rate(self):
        Quote.objects.filter(pk=self.city_quote.pk).update(inherits_base=True)
        preview = self.client.post(self.url, {
            'action': 'override_base_rate',
            '_selected_action': [str(self.city_quote.pk)],
        })
        self.assertContains(preview, 'Перевизначити курс міста')
        self.city_quote.refresh_from_db()
        self.assertTrue(self.city_quote.inherits_base)
        done = self.client.post(self.url, {
            'action': 'override_base_rate',
            '_selected_action': [str(self.city_quote.pk)],
            'confirm': 'yes',
        }, follow=True)
        self.assertContains(done, 'Перевизначено: 1.')
        self.city_quote.refresh_from_db()
        self.assertFalse(self.city_quote.inherits_base)
        self.assertEqual(self.city_quote.buy, Decimal('44.00'))
        self.base.buy = Decimal('47.00')
        self.base.sell = Decimal('48.00')
        self.base.save()
        self.assertEqual(get_quote(self.pair, self.city, RateBoard.RETAIL).buy, Decimal('44.00'))

    def test_changelist_shows_effective_rate(self):
        Quote.objects.filter(pk=self.city_quote.pk).update(inherits_base=True)
        page = self.client.get(self.url)
        self.assertContains(page, 'Наслідує')
        self.assertContains(page, '44.00')
        self.assertContains(page, '43.00')
