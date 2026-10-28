import importlib
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.db import migrations
from django.test import TestCase

from src.network.models import Branch, City

_migration = importlib.import_module(
    'src.network.migrations.0010_branch_coordinates',
)


class BranchCoordinatesMigrationTests(TestCase):
    def test_forward_and_reverse_are_noop(self):
        self.assertEqual(
            _migration.Migration.dependencies,
            [('network', '0009_clear_placeholder_branch_coords')],
        )
        self.assertEqual(len(_migration.Migration.operations), 1)
        operation = _migration.Migration.operations[0]
        self.assertIs(operation.code, migrations.RunPython.noop)
        self.assertIs(operation.reverse_code, migrations.RunPython.noop)
        source = Path(_migration.__file__).read_text(encoding='utf-8')
        self.assertIn('Intentionally empty', source)
        self.assertIn('Coordinates come from admin geocoding', source)
        self.assertNotIn('DOUBTFUL', source)
        self.assertNotIn('COORDINATES', source)

    def test_running_the_function_changes_nothing(self):
        kyiv = City.objects.create(name='Київ', slug='kyiv')
        kharkiv = City.objects.create(name='Харків', slug='kharkiv')
        poltava = City.objects.create(name='Полтава', slug='poltava')
        rows = {
            'kept': Branch.objects.create(
                city=kyiv,
                address='вул. Хрещатик, 1, Київ',
                hours='Пн–Нд, 8:00–21:00',
                phone='111',
                lat=Decimal('50.100000'),
                lng=Decimal('30.100000'),
                map_url='https://maps.example/kept',
                is_active=False,
                sort_order=2,
            ),
            'empty': Branch.objects.create(
                city=kharkiv,
                address='вул. Сумська, 10, Харків',
                hours='як було',
                phone='222',
                map_embed_url='https://www.google.com/maps/embed?pb=kh',
            ),
            'stub': Branch.objects.create(
                city=poltava,
                address='вул. Хрещатик, 1, Київ',
                hours='заглушка',
                lat=Decimal('49.500000'),
                lng=Decimal('34.500000'),
            ),
        }
        before = {}
        for key, branch in rows.items():
            branch.refresh_from_db()
            before[key] = (
                branch.address,
                branch.hours,
                branch.phone,
                branch.lat,
                branch.lng,
                branch.map_url,
                branch.map_embed_url,
                branch.is_active,
                branch.sort_order,
                branch.city_id,
            )

        with self.assertNumQueries(0):
            _migration.Migration.operations[0].code(apps, None)
            _migration.Migration.operations[0].reverse_code(apps, None)

        for key, branch in rows.items():
            branch.refresh_from_db()
            self.assertEqual(
                (
                    branch.address,
                    branch.hours,
                    branch.phone,
                    branch.lat,
                    branch.lng,
                    branch.map_url,
                    branch.map_embed_url,
                    branch.is_active,
                    branch.sort_order,
                    branch.city_id,
                ),
                before[key],
                key,
            )
        rows['empty'].refresh_from_db()
        self.assertIsNone(rows['empty'].lat)
        self.assertIsNone(rows['empty'].lng)
