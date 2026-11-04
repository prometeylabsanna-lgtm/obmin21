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

    def test_without_branch_phone_is_global_telegram_is_obmin21(self):
        data = get_contacts(self._request(None))
        self.assertEqual(data['source'], 'global')
        self.assertEqual(data['phone'], _GLOBAL)
        self.assertEqual(data['phone_href'], '+380671112233')
        self.assertEqual(data['telegram_url'], 'https://t.me/obmin21')
        self.assertEqual(data['telegram_display'], '@obmin21')
        self.assertNotEqual(data['telegram_url'], _GLOBAL_TG)
        self.assertNotIn('Obmin_Desk', data['telegram_display'])

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

    def _footer(self, html):
        start = html.find('id="footer-contacts"')
        self.assertGreaterEqual(start, 0)
        end = html.find('site-footer__bar', start)
        if end < 0:
            end = html.find('id="mobile-contacts"', start)
        self.assertGreater(end, start)
        return html[start:end]

    def test_second_branch_contacts_in_modal_and_footer(self):
        second_phone = '+38 (032) 222-22-22'
        second = Branch.objects.create(
            city=self.city,
            address='вул. Друга, 9',
            phone=second_phone,
            telegram='seconddesk',
            sort_order=1,
        )
        switched = self.client.post(
            reverse('network:set_city'),
            {'city': self.city.slug, 'branch': str(second.pk)},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(switched.status_code, 200)
        self.assertEqual(self.client.session['branch_id'], second.pk)
        self.assertEqual(
            self.client.cookies[settings.BRANCH_COOKIE_NAME].value,
            str(second.pk),
        )
        fragment = self._footer(switched.content.decode())
        self.assertIn(second_phone, fragment)
        self.assertIn('https://t.me/seconddesk', fragment)
        self.assertNotIn(_PHONE, fragment)
        self.assertNotIn('https://t.me/cashier1', fragment)

        modal = self.client.get(reverse('leads:contact_modal'))
        self.assertContains(modal, second_phone)
        self.assertContains(modal, 'https://t.me/seconddesk')
        self.assertContains(modal, '@seconddesk')
        self.assertNotContains(modal, _PHONE)
        self.assertNotContains(modal, 'https://t.me/cashier1')
        self.assertNotContains(modal, '@cashier1')

        home = self.client.get(reverse('core:home'))
        footer = self._footer(home.content.decode())
        self.assertIn(second_phone, footer)
        self.assertIn('https://t.me/seconddesk', footer)
        self.assertNotIn(_PHONE, footer)
        self.assertNotIn('https://t.me/cashier1', footer)
        self.assertEqual(self.client.session['branch_id'], second.pk)

    def test_inactive_or_foreign_branch_falls_back_to_first(self):
        inactive_phone = '+38 (032) 222-22-22'
        Branch.objects.create(
            city=self.city,
            address='вул. Закрита, 3',
            phone=inactive_phone,
            telegram='closeddesk',
            sort_order=1,
            is_active=False,
        )
        other = City.objects.create(name='Дніпро', slug='dnipro-contacts', sort_order=5)
        foreign = Branch.objects.create(
            city=other,
            address='вул. Чуже, 8',
            phone='+38 (044) 999-99-99',
            telegram='foreigndesk',
            sort_order=0,
        )
        session = self.client.session
        session['city_slug'] = self.city.slug
        session['branch_id'] = foreign.pk
        session.save()
        modal = self.client.get(reverse('leads:contact_modal'))
        self.assertContains(modal, _PHONE)
        self.assertContains(modal, 'https://t.me/cashier1')
        self.assertNotContains(modal, foreign.phone)
        self.assertNotContains(modal, 'https://t.me/foreigndesk')
        footer = self._footer(self.client.get(reverse('core:home')).content.decode())
        self.assertIn(_PHONE, footer)
        self.assertIn('https://t.me/cashier1', footer)
        self.assertNotIn(foreign.phone, footer)
        self.assertNotIn(inactive_phone, footer)

    def test_pages_without_branch_use_obmin21_and_global_phone(self):
        Branch.objects.update(is_active=False)
        City.objects.update(is_active=False)
        home = self.client.get(reverse('core:home'))
        self.assertEqual(home.status_code, 200)
        footer = self._footer(home.content.decode())
        self.assertIn('https://t.me/obmin21', footer)
        self.assertIn(_GLOBAL, footer)
        self.assertNotIn(_GLOBAL_TG, footer)
        self.assertNotIn('Obmin_Desk', footer)
        modal = self.client.get(reverse('leads:contact_modal'))
        self.assertContains(modal, 'https://t.me/obmin21')
        self.assertContains(modal, '@obmin21')
        self.assertContains(modal, _GLOBAL)
        self.assertNotContains(modal, _GLOBAL_TG)
        self.assertNotContains(modal, '@Obmin_Desk')

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
            (
                op.__class__.__name__,
                getattr(op, 'model_name', None),
                getattr(op, 'name', None),
            )
            for op in migration.Migration.operations
        ]
        kinds = [kind for kind, _model, _name in described]
        self.assertLess(kinds.index('RunPython'), kinds.index('RemoveField'))
        self.assertIn(('RemoveField', 'city', 'phone'), described)
        self.assertIn(('AddField', 'branch', 'telegram'), described)
        self.assertTrue(any(
            getattr(op, 'code', None).__name__ == 'copy_city_phone_to_branches'
            and op.reverse_code.__name__ == 'noop'
            for op in migration.Migration.operations
            if getattr(op, 'code', None)
        ))
        self.assertFalse(any(
            model == 'branch' and name == 'phone'
            for _kind, model, name in described
        ))
        self.assertTrue(any(field.name == 'phone' for field in Branch._meta.fields))
        self.assertFalse(any(field.name == 'phone' for field in City._meta.fields))
