"""Форма FAQ в адмінці підключає TinyMCE, а файловий браузер і flatpages — ні."""

from unittest import SkipTest

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from src.core.tests.eo_realdb import is_committed_sqlite


def setUpModule():
    if is_committed_sqlite(connection.settings_dict.get('NAME')):
        raise SkipTest('Тест TinyMCE не читає db.sqlite3')
    tables = set(connection.introspection.table_names())
    if 'auth_user' not in tables:
        call_command('migrate', verbosity=0, interactive=False)


class TinyMceFaqAdminTests(TestCase):
    def test_faq_add_form_loads_tinymce_without_file_endpoints(self):
        chosen, reason = _faq_admin_add()
        if chosen is None:
            self.fail(reason)
        user = get_user_model().objects.create_superuser('qa_admin')
        self.client.force_login(user)
        response = self.client.get(chosen['url'])
        self.assertEqual(
            response.status_code,
            200,
            f"{chosen['label']} {chosen['url_name']}",
        )
        html = response.content.decode()
        self.assertIn('tinymce.min.js', html)
        self.assertIn('init_tinymce.js', html)
        self.assertIsNotNone(finders.find('tinymce/tinymce.min.js'))
        self.assertIsNotNone(finders.find('django_tinymce/init_tinymce.js'))
        self.client.raise_request_exception = False
        closed = []
        for path in ('/tinymce/filebrowser/', '/tinymce/flatpages_link_list/'):
            code = self.client.get(path).status_code
            if code != 404:
                closed.append(f'{path} {code}')
        self.assertFalse(
            closed,
            f"{chosen['label']} {chosen['url_name']}\n" + '\n'.join(closed),
        )


def _faq_admin_add():
    from django.contrib import admin

    candidates = []
    for model, model_admin in admin.site._registry.items():
        meta = model._meta
        blob = f'{model.__name__} {meta.model_name}'.casefold()
        if 'faq' not in blob:
            continue
        url_name = f'admin:{meta.app_label}_{meta.model_name}_add'
        rich = tuple(sorted(getattr(model_admin, 'rich_fields', ()) or ()))
        try:
            url = reverse(url_name)
        except NoReverseMatch:
            url = ''
        candidates.append({
            'label': f'{meta.app_label}.{model.__name__}',
            'url_name': url_name,
            'url': url,
            'rich': rich,
        })
    with_add = [item for item in candidates if item['url']]
    rich = [item for item in with_add if item['rich']]
    pool = rich or with_add
    exact = [
        item for item in pool
        if item['label'].rsplit('.', 1)[-1].casefold() == 'faqitem'
    ]
    if len(exact) == 1:
        return exact[0], ''
    if len(pool) == 1:
        return pool[0], ''
    if not candidates:
        return None, 'Модель FAQ і її адмінку не знайдено в admin.site'
    lines = []
    for item in candidates:
        add = item['url_name'] if item['url'] else 'add немає'
        fields = ','.join(item['rich']) or 'без rich'
        lines.append(f"{item['label']} | {add} | {fields}")
    return None, 'Модель FAQ або її адмінку add не вибрано:\n' + '\n'.join(lines)
