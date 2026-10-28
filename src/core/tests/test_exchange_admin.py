import importlib
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.content.models import AdvantageItem, FaqItem, HomePage, HomeStat, Service
from src.core.exchange_fields import (
    EXCHANGE_SAFE_CURRENCY_HELP,
    EXCHANGE_SAFE_HELP,
)
from src.core.exchange_mode import is_mode_forced_by_env
from src.core.exchange_preview import (
    ENV_LOCK_NOTICE,
    _FALLBACK_STOP_WORDS,
    load_stop_words,
    stored_exchange_only,
)
from src.core.exchange_stopwords import STOP_WORDS
from src.core.models import ExchangeModeLog, SiteSettings
from src.rates.models import CurrencyPair, Quote
from src.reviews.models import Review

_ENV_KEYS = ('EXCHANGE_ONLY_MODE', 'HIDDEN_PAGE_STATUS')
_SAFE_MODELS = (Service, CurrencyPair, Review, Post, FaqItem, AdvantageItem, HomeStat)
_FILTER_STOPWORDS = Path(
    '/Users/olegbonislavskyi/Sites/Obmin21-wt-filter/src/core/exchange_stopwords.py'
)


def _perm(app_label, codename):
    return Permission.objects.get(
        codename=codename,
        content_type__app_label=app_label,
    )


def _flags():
    found = {}
    for model in _SAFE_MODELS:
        found[model._meta.label] = list(
            model.objects.order_by('pk').values_list('pk', 'exchange_safe'),
        )
    return found


class ExchangeAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='exchange-admin',
            email='exchange-admin@example.com',
            password='pass-12345',
        )

    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        cache.clear()
        SiteSettings.load()
        SiteSettings.objects.filter(pk=1).update(
            exchange_only=False,
            exchange_only_since=None,
        )
        cache.clear()
        self.client.force_login(self.user)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cache.clear()

    def _preview_url(self):
        return reverse('admin:core_sitesettings_exchange_only_preview', args=[1])

    def _settings_url(self):
        return reverse('admin:core_sitesettings_change', args=[1])

    def _samples(self):
        page = HomePage.load()
        category = Category.objects.create(name='Журнал етап 8', slug='zhurnal-etap-8')
        return [
            Service.objects.create(
                title='Послуга етап 8', slug='posluha-etap-8', short_desc='Текст',
            ),
            CurrencyPair.objects.create(code='PLN', name='Злотий', slug='pln-etap-8'),
            Review.objects.create(name='Іра', text='Добре'),
            Post.objects.create(
                category=category,
                title='Пост етап 8',
                slug='post-etap-8',
                body='Текст',
            ),
            FaqItem.objects.create(question='Як етап 8?', answer='Так'),
            AdvantageItem.objects.create(
                audience=AdvantageItem.Audience.CITIZENS,
                text='Пункт етап 8',
            ),
            HomeStat.objects.create(page=page, number='8', text='Клієнти етап 8'),
        ]

    def test_seven_models_show_column_filter_actions_and_help(self):
        samples = self._samples()
        for obj in samples:
            opts = obj._meta
            listing = self.client.get(
                reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'),
            )
            self.assertEqual(listing.status_code, 200)
            self.assertContains(listing, 'Показувати в режимі «Лише обмін»')
            self.assertContains(listing, 'Режим лише обмін: так/ні')
            self.assertContains(listing, 'Позначити як обмін')
            self.assertContains(listing, 'Зняти позначку')
            form = self.client.get(
                reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[obj.pk]),
            )
            self.assertEqual(form.status_code, 200)
            currency_form = isinstance(obj, (Post, Review))
            expected_help = (
                EXCHANGE_SAFE_CURRENCY_HELP if currency_form else EXCHANGE_SAFE_HELP
            )
            self.assertContains(form, expected_help)
            added = self.client.get(
                reverse(f'admin:{opts.app_label}_{opts.model_name}_add'),
            )
            self.assertEqual(added.status_code, 200)
            self.assertContains(added, 'name="exchange_safe"')
            self.assertContains(added, expected_help)
            if currency_form:
                self.assertNotContains(form, EXCHANGE_SAFE_HELP)
                self.assertNotContains(added, EXCHANGE_SAFE_HELP)

    def test_filter_limits_exchange_safe_rows(self):
        Service.objects.create(
            title='Видима послуга етап 8',
            slug='vydyma-posluha-etap-8',
            short_desc='Текст',
            exchange_safe=True,
        )
        Service.objects.create(
            title='Прихована послуга етап 8',
            slug='prykhovana-posluha-etap-8',
            short_desc='Текст',
            exchange_safe=False,
        )
        url = reverse('admin:content_service_changelist')
        hidden = self.client.get(url, {'exchange_safe': '0'})
        shown = self.client.get(url, {'exchange_safe': '1'})
        self.assertContains(hidden, 'Прихована послуга етап 8')
        self.assertNotContains(hidden, 'Видима послуга етап 8')
        self.assertContains(shown, 'Видима послуга етап 8')
        self.assertNotContains(shown, 'Прихована послуга етап 8')

    def test_bulk_actions_change_only_selected_rows(self):
        hidden = Service.objects.create(
            title='Без галочки етап 8',
            slug='bez-halochky-etap-8',
            short_desc='Текст',
            exchange_safe=False,
        )
        kept = Service.objects.create(
            title='З галочкою етап 8',
            slug='z-halochkoiu-etap-8',
            short_desc='Текст',
            exchange_safe=True,
        )
        before = _flags()
        url = reverse('admin:content_service_changelist')
        marked = self.client.post(url, {
            'action': 'mark_exchange_safe',
            '_selected_action': [str(hidden.pk)],
        }, follow=True)
        self.assertEqual(marked.status_code, 200)
        hidden.refresh_from_db()
        kept.refresh_from_db()
        self.assertTrue(hidden.exchange_safe)
        self.assertTrue(kept.exchange_safe)
        self.assertContains(marked, 'Позначено як обмін: 1.')
        cleared = self.client.post(url, {
            'action': 'clear_exchange_safe',
            '_selected_action': [str(hidden.pk)],
        }, follow=True)
        self.assertEqual(cleared.status_code, 200)
        hidden.refresh_from_db()
        kept.refresh_from_db()
        self.assertFalse(hidden.exchange_safe)
        self.assertTrue(kept.exchange_safe)
        self.assertEqual(_flags(), before)

    def test_quote_list_has_no_exchange_actions(self):
        listing = self.client.get(reverse('admin:rates_quote_changelist'))
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, 'Позначити як обмін')
        self.assertNotContains(listing, 'Зняти позначку')
        self.assertFalse(hasattr(Quote, 'exchange_safe'))

    def test_staff_without_change_cannot_bulk_mark(self):
        service = Service.objects.create(
            title='Чужа послуга етап 8',
            slug='chuzha-posluha-etap-8',
            short_desc='Текст',
        )
        staff = User.objects.create_user('viewer-etap-8', password='pass-12345', is_staff=True)
        staff.user_permissions.add(_perm('content', 'view_service'))
        self.client.force_login(staff)
        listing = self.client.get(reverse('admin:content_service_changelist'))
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, 'Позначити як обмін')
        posted = self.client.post(reverse('admin:content_service_changelist'), {
            'action': 'mark_exchange_safe',
            '_selected_action': [str(service.pk)],
        })
        service.refresh_from_db()
        self.assertFalse(service.exchange_safe)
        self.assertEqual(posted.status_code, 200)
        self.assertNotContains(posted, 'Позначено як обмін: 1.')

    def test_settings_button_opens_preview_and_post_toggles_with_log(self):
        watched = Service.objects.create(
            title='Незаймана послуга етап 8',
            slug='nezaimana-etap-8',
            short_desc='Текст',
            exchange_safe=False,
        )
        safe = Review.objects.create(name='Олег', text='Добре', exchange_safe=True)
        before = _flags()
        settings_page = self.client.get(self._settings_url())
        self.assertContains(settings_page, 'Увімкнути режим «Лише обмін валют»')
        self.assertContains(settings_page, '/exchange-only/')
        self.assertNotContains(settings_page, ENV_LOCK_NOTICE)
        preview = self.client.get(self._preview_url())
        self.assertEqual(preview.status_code, 200)
        self.assertFalse(stored_exchange_only())
        self.assertEqual(ExchangeModeLog.objects.count(), 0)
        enabled = self.client.post(self._preview_url(), follow=True)
        self.assertContains(enabled, 'Режим «Лише обмін валют» увімкнено.')
        self.assertContains(enabled, 'Вимкнути режим «Лише обмін валют»')
        self.assertTrue(stored_exchange_only())
        self.assertIsNotNone(SiteSettings.objects.get(pk=1).exchange_only_since)
        disabled = self.client.post(self._preview_url(), follow=True)
        self.assertContains(disabled, 'Режим «Лише обмін валют» вимкнено.')
        self.assertFalse(stored_exchange_only())
        self.assertIsNone(SiteSettings.objects.get(pk=1).exchange_only_since)
        logs = list(ExchangeModeLog.objects.order_by('created_at', 'pk'))
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].user, self.user)
        self.assertEqual(logs[0].source, ExchangeModeLog.Source.ADMIN)
        self.assertFalse(logs[0].from_value)
        self.assertTrue(logs[0].to_value)
        self.assertTrue(logs[1].from_value)
        self.assertFalse(logs[1].to_value)
        watched.refresh_from_db()
        safe.refresh_from_db()
        self.assertFalse(watched.exchange_safe)
        self.assertTrue(safe.exchange_safe)
        self.assertEqual(_flags(), before)

    def test_anonymous_and_staff_permissions_and_csrf(self):
        preview = self._preview_url()
        self.client.logout()
        anonymous = self.client.get(preview)
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse('admin:login'), anonymous.url)
        plain = User.objects.create_user('plain-etap-8', password='pass-12345', is_staff=False)
        self.client.force_login(plain)
        outsider = self.client.get(preview)
        self.assertEqual(outsider.status_code, 302)
        viewer = User.objects.create_user('staff-view-etap-8', password='pass-12345', is_staff=True)
        viewer.user_permissions.add(_perm('core', 'view_sitesettings'))
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(preview).status_code, 403)
        editor = User.objects.create_user('staff-edit-etap-8', password='pass-12345', is_staff=True)
        editor.user_permissions.add(_perm('core', 'change_sitesettings'))
        self.client.force_login(editor)
        self.assertEqual(self.client.get(preview).status_code, 200)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(editor)
        rejected = csrf_client.post(preview, {})
        self.assertEqual(rejected.status_code, 403)
        self.assertFalse(stored_exchange_only())
        self.assertEqual(ExchangeModeLog.objects.count(), 0)
        page = csrf_client.get(preview)
        token = csrf_client.cookies['csrftoken'].value
        accepted = csrf_client.post(
            preview,
            {'csrfmiddlewaretoken': token},
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 302)
        self.assertTrue(stored_exchange_only())
        self.assertEqual(ExchangeModeLog.objects.get().user, editor)

    def test_forced_env_disables_toggle_on_get_and_post(self):
        SiteSettings.objects.filter(pk=1).update(exchange_only=False)
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': '1'}):
            self.assertTrue(is_mode_forced_by_env())
            page = self.client.get(self._settings_url())
            self.assertContains(page, ENV_LOCK_NOTICE)
            self.assertContains(page, 'disabled')
            self.assertNotContains(page, '/exchange-only/')
            preview = self.client.get(self._preview_url())
            self.assertContains(preview, ENV_LOCK_NOTICE)
            self.assertContains(preview, 'Що буде сховано')
            self.assertNotContains(preview, 'Підтвердити увімкнення')
            self.assertNotContains(preview, 'Підтвердити вимкнення')
            posted = self.client.post(self._preview_url())
        self.assertEqual(posted.status_code, 403)
        self.assertIn(ENV_LOCK_NOTICE, posted.content.decode())
        self.assertFalse(stored_exchange_only())
        self.assertEqual(ExchangeModeLog.objects.count(), 0)
        SiteSettings.objects.filter(pk=1).update(exchange_only=True)
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': '0'}):
            locked = self.client.post(self._preview_url())
        self.assertEqual(locked.status_code, 403)
        self.assertTrue(SiteSettings.objects.get(pk=1).exchange_only)
        self.assertEqual(ExchangeModeLog.objects.count(), 0)
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': ' 1 '}):
            spaced = self.client.post(self._preview_url())
        self.assertEqual(spaced.status_code, 403)
        with patch.dict(os.environ, {'EXCHANGE_ONLY_MODE': 'yes'}):
            self.assertFalse(is_mode_forced_by_env())
            opened = self.client.get(self._settings_url())
            self.assertContains(opened, '/exchange-only/')
            self.assertNotContains(opened, ENV_LOCK_NOTICE)

    def test_mode_log_admin_is_read_only(self):
        self.client.post(self._preview_url())
        log = ExchangeModeLog.objects.get()
        listing = self.client.get(reverse('admin:core_exchangemodelog_changelist'))
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, 'exchange-admin')
        self.assertContains(listing, 'Адмінка')
        index = self.client.get(reverse('admin:index'))
        self.assertContains(index, 'Журнал режиму «Лише обмін»')
        added = self.client.get(reverse('admin:core_exchangemodelog_add'))
        self.assertEqual(added.status_code, 403)
        change = reverse('admin:core_exchangemodelog_change', args=[log.pk])
        self.assertEqual(self.client.get(change).status_code, 200)
        posted = self.client.post(change, {
            'source': 'hack',
            'from_value': 'on',
            'to_value': 'on',
        })
        self.assertEqual(posted.status_code, 403)
        log.refresh_from_db()
        self.assertEqual(log.source, ExchangeModeLog.Source.ADMIN)
        self.assertFalse(log.from_value)
        self.assertTrue(log.to_value)
        staff = User.objects.create_user('no-log-etap-8', password='pass-12345', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(
            self.client.get(reverse('admin:core_exchangemodelog_changelist')).status_code,
            403,
        )

    def test_stopwords_match_filter_module_and_fallback(self):
        words, matcher = load_stop_words()
        self.assertEqual(words, STOP_WORDS)
        self.assertEqual(_FALLBACK_STOP_WORDS, STOP_WORDS)
        self.assertTrue(matcher('Обмін криптовалюти'))
        self.assertFalse(matcher('Лише готівка'))
        real_import = __import__

        def guarded(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'src.core.exchange_stopwords':
                raise ImportError('absent')
            return real_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=guarded):
            fallback_words, fallback_matcher = load_stop_words()
        self.assertEqual(fallback_words, _FALLBACK_STOP_WORDS)
        self.assertTrue(fallback_matcher('переказ'))
        if _FILTER_STOPWORDS.is_file():
            spec = importlib.util.spec_from_file_location(
                'eo_filter_exchange_stopwords_stage8',
                _FILTER_STOPWORDS,
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(tuple(module.STOP_WORDS), STOP_WORDS)

    def test_migration_does_not_touch_exchange_safe(self):
        path = Path(__file__).resolve().parents[1] / 'migrations' / '0008_exchangemodelog.py'
        text = path.read_text(encoding='utf-8')
        self.assertIn('CreateModel', text)
        self.assertIn('ExchangeModeLog', text)
        self.assertNotIn('exchange_safe', text)
        self.assertNotIn('RunPython', text)
        migration = importlib.import_module('src.core.migrations.0008_exchangemodelog')
        for operation in migration.Migration.operations:
            self.assertNotEqual(operation.__class__.__name__, 'RunPython')
