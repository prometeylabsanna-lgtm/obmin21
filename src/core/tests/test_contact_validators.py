from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase

from src.content.models import ContactsPage
from src.core.models import SiteSettings
from src.network.models import Branch, City


class ContactValidatorsUnitTest(SimpleTestCase):
    def test_display_ua_phone_formats(self):
        from src.core.contact_validators import display_ua_phone

        self.assertEqual(display_ua_phone(''), '')
        self.assertEqual(display_ua_phone('0501112233'), '+38 (050) 111-22-33')
        self.assertEqual(
            display_ua_phone('+38(044)444 44 44'),
            '+38 (044) 444-44-44',
        )

    def test_telegram_normalizers(self):
        from src.core.contact_validators import (
            normalize_telegram_handle,
            normalize_telegram_url,
        )

        for raw in ('https://t.me/obmin21', '@obmin21', 't.me/obmin21'):
            self.assertEqual(normalize_telegram_url(raw), 'https://t.me/obmin21')
            self.assertEqual(normalize_telegram_handle(raw), '@obmin21')

        for bad in ('abc', 'https://evil.com/x'):
            with self.subTest(value=bad):
                with self.assertRaises(ValidationError):
                    normalize_telegram_url(bad)


class ContactValidatorsModelTest(TestCase):
    _DISPLAY = '+38 (099) 111-11-11'

    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(name='Тест', slug='test-contact-val')

    def _branch(self, **kwargs):
        defaults = {
            'city': self.city,
            'address': 'вул. Тестова, 1',
            'phone': '',
        }
        defaults.update(kwargs)
        return Branch(**defaults)

    def test_invalid_phone_rejected(self):
        cases = [
            ('City', City(name='X', slug='x-inv', phone='abc')),
            ('Branch', self._branch(phone='abc')),
            ('SiteSettings', SiteSettings(default_phone='abc')),
            ('ContactsPage', ContactsPage(phone='abc')),
        ]
        for label, obj in cases:
            with self.subTest(model=label):
                with self.assertRaises(ValidationError):
                    obj.full_clean()

    def test_phone_accepted_and_normalized(self):
        samples = [
            ('+38 (099) 111-11-11', '+38 (099) 111-11-11'),
            ('+38 (067) 101-01-01', '+38 (067) 101-01-01'),
            ('+38(044)444 44 44', '+38 (044) 444-44-44'),
            ('0501112233', '+38 (050) 111-22-33'),
        ]
        for index, (raw, expected) in enumerate(samples):
            with self.subTest(phone=raw):
                branch = self._branch(phone=raw)
                branch.full_clean()
                self.assertEqual(branch.phone, expected)

                city = City(name='C', slug=f'c-val-{index}', phone=raw)
                city.full_clean()
                self.assertEqual(city.phone, expected)

                site = SiteSettings(default_phone=raw)
                site.full_clean()
                self.assertEqual(site.default_phone, expected)

                page = ContactsPage(phone=raw)
                page.full_clean()
                self.assertEqual(page.phone, expected)

        branch = self._branch(phone='')
        branch.full_clean()
        self.assertEqual(branch.phone, '')

        site = SiteSettings(default_phone='')
        site.full_clean()
        self.assertEqual(site.default_phone, '')

    def test_telegram_site_settings(self):
        site = SiteSettings(telegram_url='@obmin21')
        site.full_clean()
        self.assertEqual(site.telegram_url, 'https://t.me/obmin21')

        with self.assertRaises(ValidationError):
            SiteSettings(telegram_url='abc').full_clean()

    def test_telegram_contacts_page(self):
        page = ContactsPage(telegram='t.me/obmin21')
        page.full_clean()
        self.assertEqual(page.telegram, '@obmin21')

        with self.assertRaises(ValidationError):
            ContactsPage(telegram='https://evil.com/x').full_clean()

    def test_phone_tel_filter_on_display_form(self):
        tpl = Template('{{ value|phone_tel }}')
        out = tpl.render(Context({'value': self._DISPLAY}))
        self.assertEqual(out, '+380991111111')
