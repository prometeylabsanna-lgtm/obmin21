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
apply_branch_coordinates = _migration.apply_branch_coordinates
COORDINATES = _migration.COORDINATES

_KYIV_ADDRESS = 'вул. Хрещатик, 1, Київ'
_DOUBTFUL_SLUGS = (
    'poltava',
    'sumy',
    'ivano-frankivsk',
    'kryvyi-rih',
    'kropyvnytskyi',
)
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


def _snapshot(branch):
    branch.refresh_from_db()
    return {name: getattr(branch, name) for name in _UNTOUCHED}


class BranchCoordinatesMigrationTests(TestCase):
    def test_migration_follows_0009_and_reverse_is_noop(self):
        self.assertEqual(
            _migration.Migration.dependencies,
            [('network', '0009_clear_placeholder_branch_coords')],
        )
        operation = _migration.Migration.operations[0]
        self.assertIs(operation.code, apply_branch_coordinates)
        self.assertIs(operation.reverse_code, migrations.RunPython.noop)
        source = Path(_migration.__file__).read_text(encoding='utf-8')
        self.assertIn('DOUBTFUL', source)
        self.assertIn("vinnytsia 'вул. Соборна, 30, Вінниця'", source)
        self.assertIn('geocoded only to street level', source)
        for slug in _DOUBTFUL_SLUGS:
            self.assertIn(slug, source)
        self.assertIn(_KYIV_ADDRESS, source)
        self.assertIn('not geocoded', source)

    def test_table_is_keyed_by_slug_and_exact_address(self):
        self.assertEqual(len(COORDINATES), 10)
        self.assertEqual(
            COORDINATES[('kyiv', _KYIV_ADDRESS)],
            (Decimal('50.451447'), Decimal('30.527762')),
        )
        self.assertEqual(
            COORDINATES[('kharkiv', 'вул. Сумська, 10, Харків')],
            (Decimal('49.994443'), Decimal('36.232961')),
        )
        self.assertNotIn(('vinnytsia', 'вул. Соборна, 30, Вінниця'), COORDINATES)
        for slug in _DOUBTFUL_SLUGS:
            self.assertNotIn((slug, _KYIV_ADDRESS), COORDINATES)
        slugs = {slug for slug, _address in COORDINATES}
        self.assertIn('kyiv', slugs)
        self.assertTrue(set(_DOUBTFUL_SLUGS).isdisjoint(slugs))

    def test_updates_only_exact_null_pairs_and_reverse_keeps_them(self):
        cities = {
            'kyiv': City.objects.create(name='Київ', slug='kyiv'),
            'kharkiv': City.objects.create(name='Харків', slug='kharkiv'),
            'Kharkiv': City.objects.create(name='Інший', slug='Kharkiv'),
            'vinnytsia': City.objects.create(name='Вінниця', slug='vinnytsia'),
            'odesa': City.objects.create(name='Одеса', slug='odesa'),
        }
        for slug in _DOUBTFUL_SLUGS:
            cities[slug] = City.objects.create(name=slug, slug=slug)

        rows = {
            'kyiv': Branch.objects.create(
                city=cities['kyiv'],
                address=_KYIV_ADDRESS,
                hours='Пн–Нд, 8:00–21:00',
                phone='111',
                is_active=False,
                sort_order=2,
            ),
            'kharkiv': Branch.objects.create(
                city=cities['kharkiv'],
                address='вул. Сумська, 10, Харків',
                hours='як було',
                phone='222',
                map_url='https://maps.example/kh',
                map_embed_url='https://www.google.com/maps/embed?pb=kh',
            ),
            'kharkiv-copy': Branch.objects.create(
                city=cities['kharkiv'],
                address='вул. Сумська, 10, Харків',
                hours='копія',
            ),
            'wrong-slug': Branch.objects.create(
                city=cities['Kharkiv'],
                address='вул. Сумська, 10, Харків',
            ),
            'spaced': Branch.objects.create(
                city=cities['kharkiv'],
                address='вул. Сумська, 10, Харків ',
            ),
            'other-address': Branch.objects.create(
                city=cities['kharkiv'],
                address='вул. Сумська, 11, Харків',
            ),
            'kept-coords': Branch.objects.create(
                city=cities['odesa'],
                address='вул. Дерибасівська, 5, Одеса',
                lat=Decimal('46.100000'),
                lng=Decimal('30.100000'),
                hours='не чіпати',
            ),
            'lat-only': Branch.objects.create(
                city=cities['odesa'],
                address='вул. Дерибасівська, 5, Одеса',
                lat=Decimal('46.200000'),
                hours='лише широта',
            ),
            'vinnytsia': Branch.objects.create(
                city=cities['vinnytsia'],
                address='вул. Соборна, 30, Вінниця',
                hours='сумнівно',
            ),
        }
        dnipro = City.objects.create(name='Дніпро', slug='dnipro')
        rows['lng-only'] = Branch.objects.create(
            city=dnipro,
            address='пр. Яворницького, 50, Дніпро',
            lng=Decimal('35.100000'),
        )
        for slug in _DOUBTFUL_SLUGS:
            rows[slug] = Branch.objects.create(
                city=cities[slug],
                address=_KYIV_ADDRESS,
                hours='заглушка Києва',
            )

        before = {key: _snapshot(branch) for key, branch in rows.items()}
        stored = {}
        preset = {'kept-coords', 'lat-only', 'lng-only'}
        for key, branch in rows.items():
            branch.refresh_from_db()
            stored[key] = (branch.lat, branch.lng)
            if key not in preset:
                self.assertIsNone(branch.lat, key)
                self.assertIsNone(branch.lng, key)

        migrations.RunPython.noop(apps, None)
        for key, branch in rows.items():
            branch.refresh_from_db()
            self.assertEqual((branch.lat, branch.lng), stored[key], key)

        apply_branch_coordinates(apps, None)
        apply_branch_coordinates(apps, None)
        migrations.RunPython.noop(apps, None)

        filled = {'kyiv', 'kharkiv', 'kharkiv-copy'}
        for key, branch in rows.items():
            branch.refresh_from_db()
            self.assertEqual(_snapshot(branch), before[key], key)
            if key in filled:
                lat, lng = COORDINATES[(branch.city.slug, branch.address)]
                self.assertEqual(branch.lat, lat, key)
                self.assertEqual(branch.lng, lng, key)
            else:
                self.assertEqual(branch.lat, stored[key][0], key)
                self.assertEqual(branch.lng, stored[key][1], key)

        rows['poltava'].refresh_from_db()
        self.assertIsNone(rows['poltava'].lat)
        self.assertIsNone(rows['poltava'].lng)
        self.assertNotEqual(
            (rows['poltava'].lat, rows['poltava'].lng),
            COORDINATES[('kyiv', _KYIV_ADDRESS)],
        )
