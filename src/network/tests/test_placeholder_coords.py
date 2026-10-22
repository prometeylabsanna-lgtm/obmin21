import importlib
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.db import connection, migrations
from django.test import TestCase

from src.network.models import Branch, City

_migration = importlib.import_module(
    'src.network.migrations.0009_clear_placeholder_branch_coords',
)
clear_placeholder_coords = _migration.clear_placeholder_coords
is_placeholder_coords = _migration.is_placeholder_coords

_ROOT = Path(__file__).resolve().parents[3]
_UNTOUCHED = (
    'address',
    'hours',
    'phone',
    'map_url',
    'map_embed_url',
    'is_active',
    'sort_order',
    'city_id',
)


def _untouched(branch):
    branch.refresh_from_db()
    return {name: getattr(branch, name) for name in _UNTOUCHED}


class ClearPlaceholderCoordsTests(TestCase):
    def test_migration_follows_0008_and_reverse_is_noop(self):
        self.assertEqual(
            _migration.Migration.dependencies,
            [('network', '0008_branch_map_embed_url')],
        )
        self.assertEqual(len(_migration.Migration.operations), 1)
        operation = _migration.Migration.operations[0]
        self.assertIs(operation.code, clear_placeholder_coords)
        self.assertIs(operation.reverse_code, migrations.RunPython.noop)

    def test_clears_placeholder_keeps_other_coords_and_is_idempotent(self):
        city = City.objects.create(name='Київ', slug='kyiv-coords', phone='+380')
        other = City.objects.create(name='Львів', slug='lviv-coords', phone='+380')
        rows = {
            'placeholder': Branch.objects.create(
                city=city,
                address='вул. Сумська, 10, Харків',
                hours='Пн–Нд, 8:00–21:00',
                phone='+38 (099) 111-11-11',
                lat=Decimal('1'),
                lng=Decimal('1'),
                map_url='https://maps.example/placeholder',
                map_embed_url='https://www.google.com/maps/embed?pb=placeholder',
                is_active=True,
                sort_order=3,
            ),
            'exact': Branch.objects.create(
                city=city,
                address='шість знаків',
                hours='09-18',
                phone='222',
                lat=Decimal('50.447200'),
                lng=Decimal('30.521500'),
                map_url='https://maps.example/exact',
                map_embed_url='https://www.google.com/maps/embed?pb=exact',
                is_active=False,
                sort_order=1,
            ),
            'real': Branch.objects.create(
                city=other,
                address='пл. Ринок, 12, Львів',
                hours='10-19',
                phone='333',
                lat=Decimal('49.841900'),
                lng=Decimal('24.031500'),
                map_url='https://maps.example/lviv',
                map_embed_url='https://www.google.com/maps/embed?pb=lviv',
                is_active=True,
                sort_order=4,
            ),
            'lat-only': Branch.objects.create(
                city=city,
                address='лише широта',
                lat=Decimal('50.447200'),
                lng=Decimal('30.523400'),
                map_url='https://maps.example/lat',
                map_embed_url='https://www.google.com/maps/embed?pb=lat',
            ),
            'lng-only': Branch.objects.create(
                city=city,
                address='лише довгота',
                lat=Decimal('50.450100'),
                lng=Decimal('30.521500'),
                map_url='https://maps.example/lng',
                map_embed_url='https://maps.google.com/maps?q=lng&output=embed',
            ),
            'near': Branch.objects.create(
                city=city,
                address='поруч на 1e-6',
                lat=Decimal('50.447201'),
                lng=Decimal('30.521500'),
                map_url='https://maps.example/near',
                map_embed_url='https://www.google.com/maps/embed?pb=near',
            ),
            'empty': Branch.objects.create(
                city=city,
                address='без координат',
                map_url='https://maps.example/empty',
                map_embed_url='https://www.google.com/maps/embed?pb=empty',
            ),
            'lat-null': Branch.objects.create(
                city=city,
                address='без широти',
                lng=Decimal('30.521500'),
                map_url='https://maps.example/lat-null',
                map_embed_url='https://www.google.com/maps/embed?pb=lat-null',
            ),
            'lng-null': Branch.objects.create(
                city=other,
                address='без довготи',
                lat=Decimal('50.447200'),
                map_url='https://maps.example/lng-null',
                map_embed_url='https://www.google.com/maps/embed?pb=lng-null',
            ),
        }
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE network_branch SET lat = ?, lng = ? WHERE id = ?',
                (50.4472, 30.5215, rows['placeholder'].pk),
            )

        before = {key: _untouched(branch) for key, branch in rows.items()}
        stored = {}
        for key, branch in rows.items():
            branch.refresh_from_db()
            stored[key] = (branch.lat, branch.lng)
        self.assertTrue(is_placeholder_coords(*stored['placeholder']))
        self.assertTrue(is_placeholder_coords(*stored['exact']))
        self.assertFalse(is_placeholder_coords(*stored['near']))
        self.assertIsNotNone(stored['placeholder'][0])

        migrations.RunPython.noop(apps, None)
        for key, branch in rows.items():
            branch.refresh_from_db()
            self.assertEqual((branch.lat, branch.lng), stored[key])
            self.assertEqual(_untouched(branch), before[key])

        clear_placeholder_coords(apps, None)
        clear_placeholder_coords(apps, None)

        cleared = {'placeholder', 'exact'}
        for key, branch in rows.items():
            branch.refresh_from_db()
            self.assertEqual(_untouched(branch), before[key], key)
            if key in cleared:
                self.assertIsNone(branch.lat, key)
                self.assertIsNone(branch.lng, key)
            else:
                self.assertEqual(branch.lat, stored[key][0], key)
                self.assertEqual(branch.lng, stored[key][1], key)

        migrations.RunPython.noop(apps, None)
        for key in cleared:
            rows[key].refresh_from_db()
            self.assertIsNone(rows[key].lat)
            self.assertIsNone(rows[key].lng)
            self.assertEqual(_untouched(rows[key]), before[key])


class SeedPlaceholderCoordsTests(TestCase):
    def test_seed_rerun_does_not_restore_placeholder_coords(self):
        seed = (
            _ROOT / 'src/core/management/commands/seed_demo.py'
        ).read_text(encoding='utf-8')
        self.assertNotIn('50.4472', seed)
        self.assertNotIn('30.5215', seed)

        kharkiv = City.objects.create(name='Харків', slug='kharkiv', phone='old')
        lviv = City.objects.create(name='Львів', slug='lviv', phone='old')
        placeholder = Branch.objects.create(
            city=kharkiv,
            address='тимчасова',
            hours='старий графік',
            phone='old',
            lat=Decimal('50.447200'),
            lng=Decimal('30.521500'),
            map_url='https://maps.example/old',
            map_embed_url='https://www.google.com/maps/embed?pb=seed-keep',
            is_active=True,
            sort_order=0,
        )
        real = Branch.objects.create(
            city=lviv,
            address='стара львівська',
            lat=Decimal('49.841900'),
            lng=Decimal('24.031500'),
            map_url='https://maps.example/lviv-real',
            map_embed_url='https://www.google.com/maps/embed?pb=lviv-real',
            is_active=True,
            sort_order=0,
        )
        clear_placeholder_coords(apps, None)
        placeholder.refresh_from_db()
        self.assertIsNone(placeholder.lat)
        self.assertIsNone(placeholder.lng)

        call_command('seed_demo', verbosity=0)
        call_command('seed_demo', verbosity=0)

        placeholder.refresh_from_db()
        real.refresh_from_db()
        self.assertIsNone(placeholder.lat)
        self.assertIsNone(placeholder.lng)
        self.assertEqual(placeholder.address, 'вул. Сумська, 10, Харків')
        self.assertEqual(
            placeholder.map_embed_url,
            'https://www.google.com/maps/embed?pb=seed-keep',
        )
        self.assertEqual(real.lat, Decimal('49.841900'))
        self.assertEqual(real.lng, Decimal('24.031500'))
        self.assertEqual(
            real.map_embed_url,
            'https://www.google.com/maps/embed?pb=lviv-real',
        )
        created = City.objects.get(slug='odesa').branches.get()
        self.assertIsNone(created.lat)
        self.assertIsNone(created.lng)
        self.assertFalse(
            any(is_placeholder_coords(branch.lat, branch.lng) for branch in Branch.objects.all())
        )
