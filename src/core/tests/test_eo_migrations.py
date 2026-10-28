"""Тестове зʼєднання Django не має незастосованих міграцій."""

from unittest import SkipTest

from django.core.management import call_command
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase

from src.core.tests.eo_realdb import is_committed_sqlite


def setUpModule():
    connection = connections['default']
    if is_committed_sqlite(connection.settings_dict.get('NAME')):
        raise SkipTest('Перевірка міграцій не читає db.sqlite3')
    tables = set(connection.introspection.table_names())
    if 'django_migrations' not in tables:
        call_command('migrate', verbosity=0, interactive=False)


class TestConnectionMigrationTests(TestCase):
    def test_test_connection_has_no_unapplied_migrations(self):
        connection = connections['default']
        if is_committed_sqlite(connection.settings_dict.get('NAME')):
            self.skipTest('Перевірка міграцій не читає db.sqlite3')
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            lines = [
                f'{migration.app_label}.{migration.name}'
                f' {"назад" if backwards else "вперед"}'
                for migration, backwards in plan
            ]
            self.fail(
                'Незастосовані міграції тестової бази:\n' + '\n'.join(lines),
            )
