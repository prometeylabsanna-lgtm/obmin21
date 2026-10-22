import os
import re

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.content.models import HomePage, ServicesPage
from src.core.models import SiteSettings

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_HOME_LEAD = 'EO-SVCLEAD-HOME'
_INTRO = 'EO-SVCLEAD-INTRO'
_ORIGINAL = (
    'Окрім обміну валют у мережі Обмін21 доступні грошові перекази по Україні, '
    'міжнародні перекази та обмін електронних валют — умови та підготовка до візиту нижче.'
)


class ServicesArticlesIntroTests(TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()

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

    def _set_copy(self, articles_lead, intro, articles_lead_mode='', intro_mode=''):
        home = HomePage.load()
        home.articles_lead = articles_lead
        home.articles_lead_mode = articles_lead_mode
        home.save(update_fields=['articles_lead', 'articles_lead_mode'])
        page = ServicesPage.load()
        page.intro = intro
        page.intro_mode = intro_mode
        page.save(update_fields=['intro', 'intro_mode'])

    def _html(self):
        response = self.client.get(reverse('content:services'))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _section(self, html):
        start = html.index('<section class="articles-section"')
        end = html.index('</section>', start)
        return html[start:end]

    def _lead(self, html):
        section = self._section(html)
        match = re.search(
            r'<p class="articles-section__lead">(.*?)</p>',
            section,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        return match.group(1).strip()

    def test_off_articles_lead_wins_over_intro(self):
        self._set_mode(False)
        self._set_copy(_HOME_LEAD, _INTRO)
        lead = self._lead(self._html())
        self.assertEqual(lead, _HOME_LEAD)
        self.assertNotIn(_INTRO, lead)
        self.assertNotIn(_ORIGINAL, lead)

    def test_off_intro_when_articles_lead_empty(self):
        self._set_mode(False)
        self._set_copy('', _INTRO)
        lead = self._lead(self._html())
        self.assertEqual(lead, _INTRO)
        self.assertNotIn(_ORIGINAL, lead)

    def test_off_original_when_both_empty(self):
        self._set_mode(False)
        self._set_copy('', '')
        lead = self._lead(self._html())
        self.assertEqual(lead, _ORIGINAL)

    def test_on_omits_regular_texts(self):
        self._set_mode(True)
        self._set_copy(_HOME_LEAD, _INTRO)
        section = self._section(self._html())
        self.assertNotIn('articles-section__lead', section)
        self.assertNotIn(_HOME_LEAD, section)
        self.assertNotIn(_INTRO, section)
        self.assertNotIn(_ORIGINAL, section)
