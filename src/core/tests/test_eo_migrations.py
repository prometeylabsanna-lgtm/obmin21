"""Реальний db.sqlite3 не має незастосованих міграцій. Файл відкривається лише на читання."""

import copy

from django.conf import settings
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, override_settings

from src.core.tests.eo_realdb import real_db_uri

_ALIAS = 'eo_real_ro'


class RealDatabaseMigrationTests(SimpleTestCase):
    databases = set()

    def test_real_sqlite_has_no_unapplied_migrations(self):
        configured = _readonly_database()
        databases = copy.deepcopy(settings.DATABASES)
        databases[_ALIAS] = configured
        previous = type(self).databases
        type(self).databases = frozenset(set(previous) | {_ALIAS})
        try:
            with override_settings(DATABASES=databases):
                connections.settings[_ALIAS] = configured
                try:
                    executor = MigrationExecutor(connections[_ALIAS])
                    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
                finally:
                    _drop_alias(_ALIAS)
            if plan:
                lines = [
                    f'{migration.app_label}.{migration.name}'
                    f' {"назад" if backwards else "вперед"}'
                    for migration, backwards in plan
                ]
                self.fail(
                    'Незастосовані міграції реальної db.sqlite3:\n' + '\n'.join(lines),
                )
        finally:
            type(self).databases = previous
            _drop_alias(_ALIAS)


def _readonly_database():
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': real_db_uri(),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {'uri': True},
        'TIME_ZONE': None,
        'TEST': {
            'CHARSET': None,
            'COLLATION': None,
            'MIGRATE': False,
            'MIRROR': None,
            'NAME': None,
        },
    }


def _drop_alias(alias):
    local = connections._connections
    if hasattr(local, alias):
        connections[alias].close()
        delattr(local, alias)
    if alias in connections.settings:
        del connections.settings[alias]
