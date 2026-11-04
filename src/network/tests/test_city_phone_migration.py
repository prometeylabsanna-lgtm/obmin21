from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

_FROM = [('network', '0018_alter_branch_phone_alter_city_phone')]
_TO = [('network', '0019_branch_telegram_drop_city_phone')]
_CITY_PHONE = '+38 (044) 111-22-33'
_OWN_PHONE = '+38 (032) 300-40-50'


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor


def _migrate_to_head():
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
    executor.loader.build_graph()


class CityPhoneToBranchMigrationTests(TransactionTestCase):
    serialized_rollback = True

    @classmethod
    def _fixture_setup(cls):
        cls.serialized_rollback = False
        try:
            super()._fixture_setup()
        finally:
            cls.serialized_rollback = True

    def _fixture_teardown(self):
        _migrate_to_head()
        super()._fixture_teardown()
        payload = getattr(connection, '_test_serialized_contents', None)
        if payload:
            connection.creation.deserialize_db_from_string(payload)

    def test_empty_branch_phone_copies_city_phone_own_phone_stays(self):
        try:
            executor = _migrate(_FROM)
            apps = executor.loader.project_state(_FROM).apps
            City = apps.get_model('network', 'City')
            Branch = apps.get_model('network', 'Branch')
            city = City.objects.create(
                name='Львів',
                slug='lviv-phone-copy',
                phone=_CITY_PHONE,
            )
            empty = Branch.objects.create(
                city=city,
                address='вул. Порожня, 1',
                phone='',
            )
            own = Branch.objects.create(
                city=city,
                address='вул. Своя, 2',
                phone=_OWN_PHONE,
            )
            other = City.objects.create(
                name='Інше',
                slug='other-phone-copy',
                phone='',
            )
            other_empty = Branch.objects.create(
                city=other,
                address='вул. Інша, 1',
                phone='',
            )
            empty_pk = empty.pk
            own_pk = own.pk
            other_pk = other_empty.pk

            executor = _migrate(_TO)
            apps = executor.loader.project_state(_TO).apps
            City = apps.get_model('network', 'City')
            Branch = apps.get_model('network', 'Branch')
            self.assertFalse(any(field.name == 'phone' for field in City._meta.fields))
            self.assertEqual(Branch.objects.get(pk=empty_pk).phone, _CITY_PHONE)
            self.assertEqual(Branch.objects.get(pk=own_pk).phone, _OWN_PHONE)
            self.assertEqual(Branch.objects.get(pk=other_pk).phone, '')
        finally:
            _migrate_to_head()
