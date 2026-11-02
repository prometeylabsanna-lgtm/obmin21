import re

from django.conf import settings
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
_BRANCH_A = '+38 032 111-11-11'
_BRANCH_B = '+38 032 222-22-22'
_POPUPS = ('leads:contact_modal', 'leads:calc_modal', 'leads:request_modal')


def _marked_phone(html, qa):
    match = re.search(rf'<a\b[^>]*data-qa="{qa}"[^>]*>[\s\S]*?</a>', html)
    if match is None:
        return '', ''
    block = match.group(0)
    href = re.search(r'href="tel:([^"]*)"', block)
    text = re.sub(r'<[^>]+>', ' ', block)
    return (href.group(1) if href else ''), ' '.join(text.split())


def _tels(html):
    return re.findall(r'href="tel:([^"]*)"', html)


class SitePhoneTests(TestCase):
    def setUp(self):
        cache.clear()
        site = SiteSettings.load()
        site.default_phone = _DEFAULT_PHONE
        site.save()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _city(self, slug, phone, sort_order=0):
        return City.objects.create(
            name='Львів',
            slug=slug,
            phone=phone,
            sort_order=sort_order,
        )

    def _branch(self, city, phone, sort_order=0, address='вул. Липова, 4'):
        return Branch.objects.create(
            city=city,
            address=address,
            phone=phone,
            sort_order=sort_order,
        )

    def _select(self, city, branch):
        session = self.client.session
        session.pop('city_slug', None)
        session.pop('branch_id', None)
        session.save()
        self.client.cookies[settings.CITY_COOKIE_NAME] = city.slug
        self.client.cookies[settings.BRANCH_COOKIE_NAME] = str(branch.pk)

    def _assert_tels(self, html, tel, label):
        found = _tels(html)
        self.assertTrue(found, label)
        self.assertEqual(set(found), {tel}, label)

    def _assert_chrome(self, html, tel, display, label):
        self._assert_tels(html, tel, label)
        header_tel, header_text = _marked_phone(html, 'phone')
        footer_tel, footer_text = _marked_phone(html, 'footer-phone')
        self.assertEqual(header_tel, tel, label)
        self.assertEqual(footer_tel, tel, label)
        self.assertIn(display, header_text, label)
        self.assertIn(display, footer_text, label)
        self.assertIn(f'"telephone":"{display}"', html, label)

    def _page(self, name):
        response = self.client.get(reverse(name))
        self.assertEqual(response.status_code, 200, name)
        return response.content.decode()

    def test_single_branch_phone_everywhere(self):
        tel = phone_tel(_BRANCH_PHONE)
        city = self._city('lviv-one-branch', _CITY_PHONE)
        self._branch(city, _BRANCH_PHONE)
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut-phone',
            short_desc='Готівковий обмін у касі',
        )
        home = self._page('core:home')
        self._assert_chrome(home, tel, _BRANCH_PHONE, 'home')
        self.assertIn('mobile-menu__phone', home)
        self.assertIn('site-chat__phone', home)
        self.assertNotIn(phone_tel(_CITY_PHONE), home)
        self.assertNotIn(phone_tel(_DEFAULT_PHONE), home)
        self.assertNotIn('tel:+380444444444', home)

        for name in ('content:contacts', 'content:faq', 'content:services'):
            page = self._page(name)
            self._assert_tels(page, tel, name)
            self.assertIn(f'"telephone":"{_BRANCH_PHONE}"', page, name)

        self.assertIn(f'class="svc-row__consult" href="tel:{tel}"', self._page('content:services'))

        for name in _POPUPS:
            body = self._page(name)
            self._assert_tels(body, tel, name)
            self.assertIn(_BRANCH_PHONE, body, name)
            self.assertNotIn(_CITY_PHONE, body, name)
            self.assertNotIn(_DEFAULT_PHONE, body, name)

        chat = self.client.post(reverse('bot:chat_send'), {'text': 'відділення'})
        self.assertEqual(chat.status_code, 200)
        transcript = chat.content.decode()
        self.assertIn(_BRANCH_PHONE, transcript)
        self.assertIn('Телефон:', transcript)
        self.assertNotIn(_CITY_PHONE, transcript)
        self.assertNotIn('Телефон міста:', transcript)

    def test_cookie_switches_branch_phone(self):
        city = self._city('lviv-two-branches', _CITY_PHONE)
        first = self._branch(city, _BRANCH_A, sort_order=0, address='вул. Перша, 1')
        second = self._branch(city, _BRANCH_B, sort_order=1, address='вул. Друга, 2')
        seen = []
        for branch, display in ((first, _BRANCH_A), (second, _BRANCH_B)):
            self._select(city, branch)
            tel = phone_tel(display)
            home = self._page('core:home')
            self._assert_chrome(home, tel, display, display)
            popup = self._page('leads:contact_modal')
            self._assert_tels(popup, tel, display)
            self.assertIn(display, popup)
            seen.append(tel)
        self.assertEqual(len(set(seen)), 2)
        self.assertNotEqual(seen[0], seen[1])

    def test_without_branch_cookie_uses_sort_order(self):
        city = self._city('lviv-sort-order', _CITY_PHONE)
        self._branch(city, _BRANCH_B, sort_order=5, address='вул. Пізніше, 5')
        self._branch(city, _BRANCH_A, sort_order=1, address='вул. Перше, 1')
        tel = phone_tel(_BRANCH_A)
        home = self._page('core:home')
        self._assert_chrome(home, tel, _BRANCH_A, 'sort')
        self.assertNotIn(f'href="tel:{phone_tel(_BRANCH_B)}"', home)
        popup = self._page('leads:calc_modal')
        self._assert_tels(popup, tel, 'calc')
        self.assertIn(_BRANCH_A, popup)
        self.assertNotIn(_BRANCH_B, popup)

    def test_fallbacks_city_then_default(self):
        city = self._city('lviv-fallback', _CITY_PHONE)
        branch = self._branch(city, '')
        city_tel = phone_tel(_CITY_PHONE)
        home = self._page('core:home')
        self._assert_chrome(home, city_tel, _CITY_PHONE, 'city')
        self.assertNotIn(phone_tel(_BRANCH_PHONE), home)
        self.assertNotIn(phone_tel(_DEFAULT_PHONE), home)
        popup = self._page('leads:contact_modal')
        self._assert_tels(popup, city_tel, 'popup-city')
        self.assertIn(_CITY_PHONE, popup)
        self.assertNotIn(_DEFAULT_PHONE, popup)

        branch.phone = '   '
        branch.save(update_fields=['phone'])
        city.phone = ''
        city.save(update_fields=['phone'])
        cache.clear()
        default_tel = phone_tel(_DEFAULT_PHONE)
        home = self._page('core:home')
        self._assert_chrome(home, default_tel, _DEFAULT_PHONE, 'default')
        self.assertNotIn(city_tel, home)
        popup = self._page('leads:calc_modal')
        self._assert_tels(popup, default_tel, 'popup-default')
        self.assertIn(_DEFAULT_PHONE, popup)
        self.assertNotIn(_CITY_PHONE, popup)

    def test_services_consult_hidden_without_phone(self):
        site = SiteSettings.load()
        site.default_phone = ''
        site.save()
        city = self._city('lviv-no-phone', '')
        self._branch(city, '   ')
        Service.objects.create(
            title='Обмін валют',
            slug='obmin-valyut-empty',
            short_desc='Готівковий обмін у касі',
        )
        cache.clear()
        page = self._page('content:services')
        self.assertNotIn('svc-row__consult', page)
        self.assertNotIn('href="tel:', page)
        self.assertNotIn('tel:+380444444444', page)
