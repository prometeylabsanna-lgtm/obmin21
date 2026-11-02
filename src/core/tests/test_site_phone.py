import re

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import Service
from src.core.models import SiteSettings
from src.core.phones import phone_tel
from src.network.models import Branch, City

_CITY_PHONE = '+38 099 222-22-22'
_BRANCH_PHONE = '+38 099 111-11-11'
_DEFAULT_PHONE = '+38 099 000-00-00'


def _marked_phone(html, qa):
    match = re.search(rf'<a\b[^>]*data-qa="{qa}"[^>]*>[\s\S]*?</a>', html)
    if match is None:
        return '', ''
    block = match.group(0)
    href = re.search(r'href="tel:([^"]*)"', block)
    text = re.sub(r'<[^>]+>', ' ', block)
    return (href.group(1) if href else ''), ' '.join(text.split())


class SitePhoneTests(TestCase):
    def setUp(self):
        cache.clear()
        site = SiteSettings.load()
        site.default_phone = _DEFAULT_PHONE
        site.save()
        cache.clear()
        self.city = City.objects.create(
            name='Львів',
            slug='lviv-site-phone',
            phone=_CITY_PHONE,
            sort_order=0,
        )
        Branch.objects.create(
            city=self.city,
            address='вул. Липова, 4',
            phone=_BRANCH_PHONE,
        )
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut-phone',
            short_desc='Готівковий обмін у касі',
        )

    def tearDown(self):
        cache.clear()

    def test_popups_match_header_and_footer(self):
        tel = phone_tel(_CITY_PHONE)
        branch_tel = phone_tel(_BRANCH_PHONE)
        home = self.client.get(reverse('core:home'))
        self.assertEqual(home.status_code, 200)
        html = home.content.decode()
        header_tel, header_text = _marked_phone(html, 'phone')
        footer_tel, footer_text = _marked_phone(html, 'footer-phone')
        self.assertEqual(header_tel, tel)
        self.assertEqual(footer_tel, tel)
        self.assertIn(_CITY_PHONE, header_text)
        self.assertIn(_CITY_PHONE, footer_text)
        self.assertNotIn(branch_tel, html)
        self.assertNotIn('tel:+380444444444', html)

        for name in ('leads:calc_modal', 'leads:contact_modal'):
            popup = self.client.get(reverse(name))
            self.assertEqual(popup.status_code, 200, name)
            body = popup.content.decode()
            self.assertIn(f'href="tel:{tel}"', body, name)
            self.assertIn(_CITY_PHONE, body, name)
            self.assertNotIn(branch_tel, body, name)
            self.assertNotIn(_BRANCH_PHONE, body, name)
            self.assertNotIn(phone_tel(_DEFAULT_PHONE), body, name)

        services = self.client.get(reverse('content:services'))
        self.assertEqual(services.status_code, 200)
        page = services.content.decode()
        self.assertIn(f'class="svc-row__consult" href="tel:{tel}"', page)
        self.assertNotIn('tel:+380444444444', page)

    def test_services_consult_hidden_without_phone(self):
        site = SiteSettings.load()
        site.default_phone = ''
        site.save()
        self.city.phone = ''
        self.city.save()
        cache.clear()
        page = self.client.get(reverse('content:services'))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertNotIn('svc-row__consult', html)
        self.assertNotIn('href="tel:', html)
        self.assertNotIn('tel:+380444444444', html)
