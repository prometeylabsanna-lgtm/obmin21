import importlib
import os
import sys
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import clear_url_caches, reverse, set_urlconf

from config.admin_url import normalize

_PRODUCTION_ENV = {
    'ALLOWED_HOSTS': 'obmin21.test',
    'POSTGRES_DB': 'obmin21',
    'POSTGRES_USER': 'obmin21',
    'POSTGRES_PASSWORD': 'test-only',
    'POSTGRES_HOST': '127.0.0.1',
    'POSTGRES_PORT': '5432',
}
_COOKIE_KEYS = ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE')


def _reload_urls():
    import config.urls as root_urls

    importlib.reload(root_urls)
    clear_url_caches()
    set_urlconf(None)


def _reload_production(overrides=None, *, use_defaults=False):
    env = dict(_PRODUCTION_ENV)
    if overrides:
        env.update(overrides)
    with patch.dict(os.environ, env, clear=False):
        if use_defaults:
            for key in _COOKIE_KEYS:
                os.environ.pop(key, None)
        if 'config.settings.production' in sys.modules:
            return importlib.reload(sys.modules['config.settings.production'])
        return importlib.import_module('config.settings.production')


class NormalizeAdminUrlTests(SimpleTestCase):
    def test_leading_slash_and_trailing_slash(self):
        self.assertEqual(normalize('/x'), 'x/')
        self.assertEqual(normalize('x'), 'x/')
        self.assertEqual(normalize('/x/'), 'x/')

    def test_empty_and_none_become_admin(self):
        self.assertEqual(normalize(''), 'admin/')
        self.assertEqual(normalize(None), 'admin/')
        self.assertEqual(normalize('   '), 'admin/')
        self.assertEqual(normalize('/'), 'admin/')
        self.assertEqual(normalize('/admin/'), 'admin/')


class DefaultAdminUrlTests(TestCase):
    def test_default_login_is_reachable(self):
        self.assertEqual(settings.ADMIN_URL, 'admin/')
        self.assertEqual(settings.UNFOLD['LOGIN']['redirect_after'], '/admin/')
        response = self.client.get('/admin/login/')
        self.assertIn(response.status_code, (200, 302))

    def test_robots_disallow_default_admin_path(self):
        response = self.client.get(reverse('core:robots'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Disallow: /admin/', body)


class CustomAdminUrlTests(TestCase):
    def test_secret_panel_hides_default_and_robots(self):
        try:
            with override_settings(ADMIN_URL='test-secret-panel/'):
                _reload_urls()
                login = self.client.get('/test-secret-panel/login/')
                self.assertEqual(login.status_code, 200)
                self.assertEqual(self.client.get('/admin/').status_code, 404)
                self.assertEqual(self.client.get('/admin/login/').status_code, 404)
                robots = self.client.get(reverse('core:robots'))
                body = robots.content.decode()
                self.assertNotIn('test-secret-panel', body)
                self.assertNotIn('Disallow: /admin/', body)
        finally:
            _reload_urls()


class ProductionCookieSecureTests(SimpleTestCase):
    def test_secure_flags_default_true_and_parse_false_values(self):
        default = _reload_production(use_defaults=True)
        self.assertIs(default.SESSION_COOKIE_SECURE, True)
        self.assertIs(default.CSRF_COOKIE_SECURE, True)

        disabled = _reload_production({
            'SESSION_COOKIE_SECURE': 'false',
            'CSRF_COOKIE_SECURE': 'false',
        })
        self.assertIs(disabled.SESSION_COOKIE_SECURE, False)
        self.assertIs(disabled.CSRF_COOKIE_SECURE, False)

        numeric = _reload_production({
            'SESSION_COOKIE_SECURE': '0',
            'CSRF_COOKIE_SECURE': '0',
        })
        self.assertIs(numeric.SESSION_COOKIE_SECURE, False)
        self.assertIs(numeric.CSRF_COOKIE_SECURE, False)
