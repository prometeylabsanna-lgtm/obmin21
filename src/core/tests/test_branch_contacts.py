import importlib
import json

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from src.core.contact_validators import normalize_telegram_username
from src.core.models import SiteSettings
from src.core.phones import get_contacts
from src.network.models import Branch, City

_PHONE = '+38 (032) 300-40-50'
_GLOBAL = '+38 (067) 111-22-33'
_GLOBAL_TG = 'https://t.me/s/Obmin_Desk?start=1'


class TelegramUsernameTests(TestCase):
    def test_accepts_every_form_and_stores_username(self):
        samples = (
            '@obmin21',
            'obmin21',
            't.me/obmin21',
            'https://t.me/obmin21',
            'https://t.me/obmin21/',
            'https://www.t.me/obmin21',
            'http://telegram.me/obmin21',
            'HTTP://T.ME/Obmin_Desk',
        )
        expected = (
            'obmin21',
            'obmin21',
            'obmin21',
            'obmin21',
            'obmin21',
            'obmin21',
            'obmin21',
            'Obmin_Desk',
        )
        city = City.objects.create(name='Львів', slug='lviv-tg-norm')
        for raw, name in zip(samples, expected):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_telegram_username(raw), name)
                branch = Branch(
                    city=city,
                    address='вул. Липова, 4',
                    phone='',
                    telegram=raw,
                )
                branch.full_clean()
                self.assertEqual(branch.telegram, name)
                self.assertEqual(branch.telegram_url, f'https://t.me/{name}')
                self.assertEqual(branch.telegram_display, f'@{name}')

        stored = Branch.objects.create(
            city=city,
            address='вул. Збережена, 1',
            telegram='https://t.me/cashier/',
        )
        stored.refresh_from_db()
        self.assertEqual(stored.telegram, 'cashier')
        self.assertEqual(stored.telegram_url, 'https://t.me/cashier')
        self.assertEqual(stored.telegram_display, '@cashier')

    def test_rejects_invalid_with_ukrainian_message(self):
        invalid = (
            'nick',
            'abc',
            'obmin-21',
            'obmin 21',
            '@nick',
            'https://evil.com/obmin21',
            'https://t.me/obmin21/extra',
            'https://t.me/obmin21?start=1',
            'https://t.me/obmin21#top',
            'user:pass@t.me/obmin21',
        )
        city = City.objects.create(name='Львів', slug='lviv-tg-bad')
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError) as caught:
                    normalize_telegram_username(raw)
                self.assertIn('нік', str(caught.exception).casefold())
                branch = Branch(
                    city=city,
                    address='вул. Липова, 4',
                    telegram=raw,
                )
                with self.assertRaises(ValidationError) as model_error:
                    branch.full_clean()
                self.assertIn('telegram', model_error.exception.message_dict)

    def test_blank_stays_blank(self):
        self.assertEqual(normalize_telegram_username(''), '')
        self.assertEqual(normalize_telegram_username('   '), '')
        city = City.objects.create(name='Львів', slug='lviv-tg-blank')
        branch = Branch.objects.create(city=city, address='вул. Порожня, 1', telegram='  ')
        self.assertEqual(branch.telegram, '')
        self.assertEqual(branch.telegram_url, '')
        self.assertEqual(branch.telegram_display, '')


class BranchContactSelectionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.site = SiteSettings.load()
        self.site.default_phone = _GLOBAL
        self.site.telegram_url = _GLOBAL_TG
        self.site.save()
        cache.clear()
        self.city = City.objects.create(name='Львів', slug='lviv-contacts', sort_order=0)
        self.branch = Branch.objects.create(
            city=self.city,
            address='вул. Липова, 4',
            phone=_PHONE,
            telegram='https://t.me/cashier1',
            sort_order=0,
        )

    def tearDown(self):
        cache.clear()

    def _request(self, branch):
        request = RequestFactory().get('/')
        request.active_branch = branch
        return request

    def _choose(self, branch):
        session = self.client.session
        session.pop('city_slug', None)
        session.pop('branch_id', None)
        session.save()
        self.client.cookies[settings.CITY_COOKIE_NAME] = branch.city.slug
        self.client.cookies[settings.BRANCH_COOKIE_NAME] = str(branch.pk)

    def test_branch_phone_and_telegram(self):
        data = get_contacts(self._request(self.branch))
        self.assertEqual(data['phone'], _PHONE)
        self.assertEqual(data['phone_href'], '+380323004050')
        self.assertEqual(data['telegram_url'], 'https://t.me/cashier1')
        self.assertEqual(data['telegram_display'], '@cashier1')
        self.assertEqual(data['source'], 'branch')

    def test_empty_telegram_falls_back_to_obmin21(self):
        self.branch.telegram = ''
        self.branch.save(update_fields=['telegram'])
        data = get_contacts(self._request(self.branch))
        self.assertEqual(data['source'], 'branch')
        self.assertEqual(data['phone'], _PHONE)
        self.assertEqual(data['telegram_url'], 'https://t.me/obmin21')
        self.assertEqual(data['telegram_display'], '@obmin21')

    def test_empty_phone_uses_global_and_keeps_branch_telegram(self):
        self.branch.phone = ''
        self.branch.save(update_fields=['phone'])
        data = get_contacts(self._request(self.branch))
        self.assertEqual(data['source'], 'global')
        self.assertEqual(data['phone'], _GLOBAL)
        self.assertEqual(data['telegram_display'], '@cashier1')

    def test_without_branch_uses_global_contacts(self):
        data = get_contacts(self._request(None))
        self.assertEqual(data['source'], 'global')
        self.assertEqual(data['phone'], _GLOBAL)
        self.assertEqual(data['telegram_url'], _GLOBAL_TG)
        self.assertEqual(data['telegram_display'], '@Obmin_Desk')

    def test_helper_is_cached_on_the_request(self):
        request = self._request(self.branch)
        first = get_contacts(request)
        with self.assertNumQueries(0):
            second = get_contacts(request)
        self.assertEqual(first, second)
        fresh = self._request(self.branch)
        with CaptureQueriesContext(connection) as captured:
            get_contacts(fresh)
        sql = ' '.join(item['sql'] for item in captured.captured_queries)
        self.assertNotIn('network_branch', sql)
        self.assertNotIn('network_city', sql)

    def test_modal_uses_selected_branch_and_query_count_is_stable(self):
        self._choose(self.branch)
        url = reverse('leads:contact_modal')
        self.client.get(url)
        with CaptureQueriesContext(connection) as before:
            first = self.client.get(url)
        self.assertContains(first, _PHONE)
        self.assertContains(first, 'https://t.me/cashier1')
        self.assertContains(first, '@cashier1')
        for index in range(3):
            Branch.objects.create(
                city=self.city,
                address=f'вул. Запасна, {index}',
                phone='+38 (044) 200-30-40',
                telegram='https://t.me/extra21',
                sort_order=index + 1,
            )
        with CaptureQueriesContext(connection) as after:
            second = self.client.get(url)
        self.assertEqual(len(after), len(before))
        self.assertContains(second, _PHONE)
        self.assertNotContains(second, '+38 (044) 200-30-40')

    def test_switch_updates_header_footer_and_mobile_contacts(self):
        response = self.client.post(
            reverse('network:set_city'),
            {'city': self.city.slug, 'branch': str(self.branch.pk)},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(set(json.loads(response['HX-Trigger'])), {'cityChanged'})
        self.assertIn('id="footer-contacts"', html)
        self.assertIn('id="mobile-contacts"', html)
        self.assertIn('id="site-chat-brand"', html)
        self.assertIn('hx-swap-oob="outerHTML"', html)
        self.assertIn(_PHONE, html)
        self.assertIn('https://t.me/cashier1', html)
        cards = self.client.get(reverse('content:contacts_cards'))
        self.assertContains(cards, _PHONE)
        self.assertContains(cards, '@cashier1')

    def test_migration_drops_city_phone_and_keeps_branch_phone(self):
        migration = importlib.import_module(
            'src.network.migrations.0019_branch_telegram_drop_city_phone',
        )
        described = [
            (op.__class__.__name__, op.model_name, getattr(op, 'name', None))
            for op in migration.Migration.operations
        ]
        self.assertIn(('RemoveField', 'city', 'phone'), described)
        self.assertIn(('AddField', 'branch', 'telegram'), described)
        self.assertFalse(any(
            model == 'branch' and name == 'phone'
            for _kind, model, name in described
        ))
        self.assertTrue(any(field.name == 'phone' for field in Branch._meta.fields))
        self.assertFalse(any(field.name == 'phone' for field in City._meta.fields))
