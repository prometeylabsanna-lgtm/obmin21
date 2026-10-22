import os
import re
from html import unescape

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage
from src.core.models import SiteSettings
from src.network.models import Branch, City

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_ADDRESS = 'вул. Дерибасівська, 5'


def _model_value(obj, name):
    value = getattr(obj, name)
    if callable(value):
        return value()
    return value


class HomeMapTemplateTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        page = HomePage.load()
        page.show_map = True
        page.save(update_fields=['show_map'])

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
            slug='odesa-map',
            phone='+380481112233',
            sort_order=0,
        )

    def _branch(self):
        return Branch.objects.create(
            city=self._city(),
            address=_ADDRESS,
            lat=None,
            lng=None,
        )

    def _home(self):
        return self.client.get(reverse('core:home'))

    def _section(self, html):
        start = html.index('data-qa="section-map"')
        end = html.index('</section>', start)
        return html[start:end]

    def _assert_branch_map(self, html, branch):
        section = self._section(html)
        iframe = re.search(r'<iframe\b([^>]*)>', section, re.DOTALL)
        self.assertIsNotNone(iframe)
        src = re.search(r'\bsrc="([^"]*)"', iframe.group(1))
        title = re.search(r'\btitle="([^"]*)"', iframe.group(1))
        self.assertIsNotNone(src)
        self.assertIsNotNone(title)
        self.assertEqual(unescape(src.group(1)), _model_value(branch, 'map_embed_src'))
        self.assertIn(branch.address, unescape(title.group(1)))
        link = re.search(
            r'class="btn map-section__btn"[^>]*\bhref="([^"]*)"',
            section,
            re.DOTALL,
        )
        self.assertIsNotNone(link)
        self.assertEqual(unescape(link.group(1)), _model_value(branch, 'map_route_url'))
        self.assertIn(branch.address, section)
        self.assertNotIn('Хрещатик', html)
        self.assertNotIn('q=Київ', html)

    def test_branch_map_uses_model_urls(self):
        self._set_mode(False)
        branch = self._branch()
        response = self._home()
        self.assertEqual(response.status_code, 200)
        self._assert_branch_map(response.content.decode(), branch)

    def test_without_branches_omits_iframe_and_fallback(self):
        self._set_mode(False)
        self._city()
        response = self._home()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        section = self._section(html)
        self.assertNotIn('<iframe', section)
        self.assertNotIn('map-section__btn', section)
        self.assertNotIn('Адреса:', section)
        self.assertNotIn('Хрещатик', html)
        self.assertNotIn('q=Київ', html)

    def test_mode_on_renders_branch_map(self):
        self._set_mode(True)
        branch = self._branch()
        response = self._home()
        self.assertEqual(response.status_code, 200)
        self._assert_branch_map(response.content.decode(), branch)
