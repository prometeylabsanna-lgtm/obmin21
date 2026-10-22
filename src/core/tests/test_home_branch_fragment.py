import os
import re
from html import unescape

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings
from src.network.models import Branch, City

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_STOPS = (
    'переказ',
    'золот',
    'оптов',
    'зношен',
    'крипт',
    'swift',
    'bitcoin',
    'замін',
)
_HOURS_A = 'Пн–Пт 08:15–17:15'
_HOURS_B = 'Вт–Сб 11:30–19:30'
_ADDRESS_A = 'вул. Коперника, 7'
_ADDRESS_B = 'просп. Соборний, 18'
_PHONE_A = '+380322210011'
_PHONE_B = '+380532220022'
_ROUTE_A = 'https://maps.example.test/route-a'
_ROUTE_B = 'https://maps.example.test/route-b'


class HomeBranchFragmentTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = HomePage.load()
        page.show_map = True
        page.save(update_fields=['show_map'])
        self.hours_label = page.map_hours_label

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _set_mode(self, enabled):
        SiteSettings.objects.filter(pk=1).update(exchange_only=enabled)
        cache.clear()

    def _city(self, name, slug, phone, sort_order):
        return City.objects.create(
            name=name,
            slug=slug,
            phone=phone,
            sort_order=sort_order,
        )

    def _branch(self, city, address, hours, phone, route):
        return Branch.objects.create(
            city=city,
            address=address,
            hours=hours,
            phone=phone,
            map_url=route,
        )

    def _fragment(self):
        return self.client.get(reverse('core:home_branch'))

    def _assert_branch(self, html, branch):
        text = unescape(html)
        self.assertIn(branch.address, text)
        self.assertIn(branch.phone, text)
        self.assertIn(branch.hours, text)
        iframe = re.search(r'<iframe\b([^>]*)>', text, re.DOTALL)
        self.assertIsNotNone(iframe)
        src = re.search(r'\bsrc="([^"]*)"', iframe.group(1))
        title = re.search(r'\btitle="([^"]*)"', iframe.group(1))
        self.assertIsNotNone(src)
        self.assertIsNotNone(title)
        self.assertEqual(src.group(1), branch.map_embed_src())
        self.assertIn(branch.address, title.group(1))
        link = re.search(
            r'class="btn map-section__btn"[^>]*\bhref="([^"]*)"',
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(link)
        self.assertEqual(link.group(1), branch.map_route_url())

    def _assert_branch_absent(self, html, branch):
        text = unescape(html)
        self.assertNotIn(branch.address, text)
        self.assertNotIn(branch.phone, text)
        self.assertNotIn(branch.hours, text)
        self.assertNotIn(branch.map_embed_src(), text)
        self.assertNotIn(branch.map_route_url(), text)

    def test_fragment_follows_set_city(self):
        self._set_mode(False)
        city_a = self._city('Львів', 'lviv-branch-a', '+380322210001', 0)
        city_b = self._city('Полтава', 'poltava-branch-b', '+380532220002', 1)
        branch_a = self._branch(city_a, _ADDRESS_A, _HOURS_A, _PHONE_A, _ROUTE_A)
        branch_b = self._branch(city_b, _ADDRESS_B, _HOURS_B, _PHONE_B, _ROUTE_B)

        before = self._fragment()
        self.assertEqual(before.status_code, 200)
        before_html = before.content.decode()
        self._assert_branch(before_html, branch_a)
        self._assert_branch_absent(before_html, branch_b)

        switched = self.client.post(
            reverse('network:set_city'),
            {'city': city_b.slug},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(switched.status_code, 200)
        self.assertIn('cityChanged', switched['HX-Trigger'])
        self.assertEqual(self.client.session['city_slug'], city_b.slug)
        self.assertEqual(
            self.client.cookies[settings.CITY_COOKIE_NAME].value,
            city_b.slug,
        )

        after = self._fragment()
        self.assertEqual(after.status_code, 200)
        html = after.content.decode()
        self.assertNotIn('id="home-branch"', html)
        self._assert_branch(html, branch_b)
        self._assert_branch_absent(html, branch_a)

    def test_without_branches_omits_hours_and_iframe(self):
        self._set_mode(False)
        self._city('Черкаси', 'cherkasy-branch', '+380472330033', 0)
        response = self._fragment()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('<iframe', html)
        self.assertNotIn('map-section__frame', html)
        self.assertNotIn(self.hours_label, html)
        self.assertIsNone(re.search(
            r'<div class="map-section__label">' + re.escape(self.hours_label),
            html,
        ))

    def test_mode_on_fragment_has_no_stop_words(self):
        self._set_mode(True)
        city = self._city('Рівне', 'rivne-branch', '+380362440044', 0)
        self._branch(city, 'вул. Липова, 4', 'Пн–Сб 09:00–18:00', '+380362440045', _ROUTE_B)
        response = self._fragment()
        self.assertEqual(response.status_code, 200)
        lowered = response.content.decode().lower()
        for token in _STOPS:
            self.assertNotIn(token, lowered, token)

    def test_home_contains_branch_block_in_both_modes(self):
        self._city('Львів', 'lviv-home-block', '+380322210099', 0)
        url = reverse('core:home_branch')
        for enabled in (False, True):
            self._set_mode(enabled)
            response = self.client.get(reverse('core:home'))
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            self.assertEqual(html.count('id="home-branch"'), 1)
            self.assertIn('hx-trigger="cityChanged from:body"', html)
            self.assertIn('hx-swap="innerHTML"', html)
            self.assertIn(f'hx-get="{url}"', html)
            self.assertIn('map-section__info', html)
            self.assertIn('data-qa="section-map"', html)
