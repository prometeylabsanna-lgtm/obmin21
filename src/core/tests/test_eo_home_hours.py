import os
import re

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings
from src.network.models import Branch, City

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_HOURS = 'Вт–Сб 11:15–17:45'
_ADDRESS = 'вул. Годинникова, 3'


class HomeHoursTemplateTests(TestCase):
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

    def _city(self):
        return City.objects.create(
            name='Одеса',
            slug='odesa-hours',
            phone='+380481112233',
            sort_order=0,
        )

    def _branch(self, hours):
        return Branch.objects.create(
            city=self._city(),
            address=_ADDRESS,
            hours=hours,
        )

    def _home(self):
        return self.client.get(reverse('core:home'))

    def _section(self, html):
        start = html.index('data-qa="section-map"')
        end = html.index('</section>', start)
        return html[start:end]

    def _hours_block(self, section):
        label = re.escape(self.hours_label)
        return re.search(
            rf'<div>\s*<div class="map-section__label">{label}</div>\s*'
            rf'<div>(.*?)</div>\s*</div>',
            section,
            re.DOTALL,
        )

    def _assert_hours_shown(self, html):
        block = self._hours_block(self._section(html))
        self.assertIsNotNone(block)
        self.assertEqual(block.group(1).strip(), _HOURS)

    def _assert_hours_hidden(self, html):
        section = self._section(html)
        self.assertNotIn('09:00', html)
        self.assertIsNone(self._hours_block(section))
        self.assertNotIn(self.hours_label, section)

    def test_branch_hours_rendered(self):
        self._set_mode(False)
        self._branch(_HOURS)
        response = self._home()
        self.assertEqual(response.status_code, 200)
        self._assert_hours_shown(response.content.decode())

    def test_empty_hours_omits_block(self):
        self._set_mode(False)
        self._branch('')
        response = self._home()
        self.assertEqual(response.status_code, 200)
        self._assert_hours_hidden(response.content.decode())

    def test_without_branches_omits_hours(self):
        self._set_mode(False)
        self._city()
        response = self._home()
        self.assertEqual(response.status_code, 200)
        self._assert_hours_hidden(response.content.decode())

    def test_mode_on_renders_branch_hours(self):
        self._set_mode(True)
        self._branch(_HOURS)
        response = self._home()
        self.assertEqual(response.status_code, 200)
        self._assert_hours_shown(response.content.decode())
