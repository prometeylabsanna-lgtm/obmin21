import os
from types import SimpleNamespace

from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from src.content.models import AdvantagesPage, HomePage
from src.core.exchange_mode import is_exchange_only, mode_text
from src.core.models import SiteSettings

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')

_US_ORIG = '<ul><li>ZZ-CMP-US-ORIG</li></ul>'
_THEM_ORIG = '<ul><li>ZZ-CMP-THEM-ORIG</li></ul>'
_US_MODE = '<ul><li>ZZ-CMP-US-MODE</li></ul>'
_THEM_MODE = '<ul><li>ZZ-CMP-THEM-MODE</li></ul>'
_SVC_ORIG = 'ZZ-SVC-LEAD-ORIG'
_ART_ORIG = 'ZZ-ART-LEAD-ORIG'
_ART_MODE = 'ZZ-ART-LEAD-MODE'


class _ModeCase(TestCase):
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


class ModeTextTests(_ModeCase):
    def test_outside_mode_returns_field_unchanged(self):
        self._set_mode(False)
        sentinel = object()
        obj = SimpleNamespace(title=sentinel, title_mode='MODE')
        self.assertIs(mode_text(obj, 'title'), sentinel)
        spaced = SimpleNamespace(title='  ORIG  ', title_mode='MODE')
        self.assertEqual(mode_text(spaced, 'title'), '  ORIG  ')

    def test_mode_returns_stripped_mode_value(self):
        self._set_mode(True)
        obj = SimpleNamespace(title='ORIG', title_mode='  MODE  ')
        self.assertEqual(mode_text(obj, 'title'), 'MODE')

    def test_blank_mode_value_does_not_fall_back(self):
        self._set_mode(True)
        for mode_value in ('', '   ', '\n\t', None):
            obj = SimpleNamespace(title='ORIG', title_mode=mode_value)
            self.assertEqual(mode_text(obj, 'title'), '')

    def test_missing_mode_attribute_returns_empty(self):
        self._set_mode(True)
        plain = SimpleNamespace(services_lead=_SVC_ORIG)
        self.assertFalse(hasattr(plain, 'services_lead_mode'))
        self.assertEqual(mode_text(plain, 'services_lead'), '')
        page = HomePage.load()
        page.services_lead = _SVC_ORIG
        with self.assertRaises(FieldDoesNotExist):
            HomePage._meta.get_field('services_lead_mode')
        self.assertEqual(mode_text(page, 'services_lead'), '')

    def test_request_selects_cached_mode(self):
        self._set_mode(False)
        request = RequestFactory().get('/')
        self.assertFalse(is_exchange_only(request))
        self._set_mode(True)
        obj = SimpleNamespace(title='ORIG', title_mode='MODE')
        self.assertEqual(mode_text(obj, 'title', request), 'ORIG')
        self.assertEqual(mode_text(obj, 'title'), 'MODE')
        fresh = RequestFactory().get('/')
        self.assertEqual(mode_text(obj, 'title', fresh), 'MODE')

    def test_mode_field_template_tag(self):
        template = Template(
            '{% load exchange_mode %}'
            "{% mode_field obj 'title' as x %}"
            '{% if x %}{{ x }}{% endif %}',
        )
        obj = SimpleNamespace(title='ORIG', title_mode='  MODE  ')
        self._set_mode(True)
        shown = template.render(Context({
            'obj': obj,
            'request': RequestFactory().get('/'),
        }))
        self.assertEqual(shown, 'MODE')
        self._set_mode(False)
        original = template.render(Context({
            'obj': obj,
            'request': RequestFactory().get('/'),
        }))
        self.assertEqual(original, 'ORIG')
        missing = SimpleNamespace(title='ORIG')
        self._set_mode(True)
        hidden = template.render(Context({
            'obj': missing,
            'request': RequestFactory().get('/'),
        }))
        self.assertEqual(hidden, '')


class ModeFieldPageTests(_ModeCase):
    def setUp(self):
        super().setUp()
        self._set_mode(False)
        self.adv = AdvantagesPage.load()
        self.adv.cmp_us_html = _US_ORIG
        self.adv.cmp_them_html = _THEM_ORIG
        self.adv.cmp_us_html_mode = ''
        self.adv.cmp_them_html_mode = ''
        self.adv.save()
        self.home = HomePage.load()
        self.home.services_lead = _SVC_ORIG
        self.home.articles_lead = _ART_ORIG
        self.home.articles_lead_mode = ''
        self.home.reviews_lead = ''
        self.home.show_services = True
        self.home.show_articles = True
        self.home.save()

    def test_mode_fields_present_except_services_lead(self):
        HomePage._meta.get_field('articles_lead_mode')
        AdvantagesPage._meta.get_field('cmp_us_html_mode')
        AdvantagesPage._meta.get_field('cmp_them_html_mode')
        with self.assertRaises(FieldDoesNotExist):
            HomePage._meta.get_field('services_lead_mode')

    def test_blank_mode_hides_original_blocks(self):
        self.adv.cmp_us_html_mode = '   '
        self.adv.cmp_them_html_mode = '\n\t'
        self.adv.save(update_fields=['cmp_us_html_mode', 'cmp_them_html_mode'])
        self.home.articles_lead_mode = '  '
        self.home.save(update_fields=['articles_lead_mode'])
        self._set_mode(True)

        advantages = self.client.get('/perevahy/')
        self.assertNotContains(advantages, 'ZZ-CMP-US-ORIG')
        self.assertNotContains(advantages, 'ZZ-CMP-THEM-ORIG')
        self.assertNotContains(advantages, 'cmp-adv__html')

        home = self.client.get('/')
        self.assertNotContains(home, _SVC_ORIG)
        self.assertNotContains(home, _ART_ORIG)
        self.assertNotContains(home, 'services-section__lead')
        self.assertNotContains(home, 'articles-section__lead')

    def test_filled_mode_fields_replace_original(self):
        self.adv.cmp_us_html_mode = _US_MODE
        self.adv.cmp_them_html_mode = _THEM_MODE
        self.adv.save(update_fields=['cmp_us_html_mode', 'cmp_them_html_mode'])
        self.home.articles_lead_mode = _ART_MODE
        self.home.save(update_fields=['articles_lead_mode'])
        self._set_mode(True)

        advantages = self.client.get('/perevahy/')
        self.assertContains(
            advantages,
            '<div class="cmp-adv__html">' + _US_MODE + '</div>',
        )
        self.assertContains(
            advantages,
            '<div class="cmp-adv__html cmp-adv__html--them">' + _THEM_MODE + '</div>',
        )
        self.assertNotContains(advantages, 'ZZ-CMP-US-ORIG')
        self.assertNotContains(advantages, 'ZZ-CMP-THEM-ORIG')

        home = self.client.get('/')
        self.assertContains(
            home,
            '<p class="articles-section__lead">' + _ART_MODE + '</p>',
        )
        self.assertNotContains(home, _ART_ORIG)
        self.assertNotContains(home, _SVC_ORIG)
        self.assertNotContains(home, 'services-section__lead')

    def test_outside_mode_pages_show_original(self):
        self.adv.cmp_us_html_mode = _US_MODE
        self.adv.cmp_them_html_mode = _THEM_MODE
        self.adv.save(update_fields=['cmp_us_html_mode', 'cmp_them_html_mode'])
        self.home.articles_lead_mode = _ART_MODE
        self.home.save(update_fields=['articles_lead_mode'])
        self._set_mode(False)

        advantages = self.client.get('/perevahy/')
        self.assertContains(
            advantages,
            '<div class="cmp-adv__html">' + _US_ORIG + '</div>',
        )
        self.assertContains(
            advantages,
            '<div class="cmp-adv__html cmp-adv__html--them">' + _THEM_ORIG + '</div>',
        )
        self.assertNotContains(advantages, 'ZZ-CMP-US-MODE')
        self.assertNotContains(advantages, 'ZZ-CMP-THEM-MODE')

        home = self.client.get('/')
        self.assertContains(
            home,
            '<p class="services-section__lead">' + _SVC_ORIG + '</p>',
        )
        self.assertContains(
            home,
            '<p class="articles-section__lead">' + _ART_ORIG + '</p>',
        )
        self.assertNotContains(home, _ART_MODE)
