import importlib
import os
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from urllib.parse import quote_plus

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase, override_settings

from src.core.slugs import latin_slug
from src.network.branch_sync import BRANCH_POINTS, apply_branch_catalog, points_by_slug
from src.network.models import Branch, BranchOpeningHours, City

_NEW_CITY_NAMES = (
    'Луцьк',
    'Житомир',
    'Чернігів',
    'Тернопіль',
    'Чернівці',
)


def _snapshot():
    cities = list(
        City.objects.order_by('pk').values(
            'pk', 'name', 'slug', 'phone', 'is_active', 'sort_order', 'name_mode',
        ),
    )
    branches = list(
        Branch.objects.order_by('pk').values(
            'pk', 'city_id', 'name', 'address', 'hours', 'phone',
            'lat', 'lng', 'coords_manual', 'map_url', 'map_embed_url',
            'is_active', 'sort_order',
        ),
    )
    hours = list(
        BranchOpeningHours.objects.order_by('pk').values(
            'pk', 'branch_id', 'day_of_week', 'opens', 'closes', 'is_closed',
        ),
    )
    return cities, branches, hours


class BranchCatalogTests(TestCase):
    def test_eighteen_points_and_known_slugs(self):
        self.assertEqual(len(BRANCH_POINTS), 18)
        self.assertEqual(len({point.slug for point in BRANCH_POINTS}), 17)
        by_slug = dict(points_by_slug())
        self.assertEqual(
            [point.address for point in by_slug['kharkiv']],
            ['вул. Кацарська, 36/38', 'метро Академіка Барабашова'],
        )
        self.assertEqual(
            [point.branch_name for point in by_slug['kharkiv']],
            ['', 'Барабашово'],
        )
        expected = {
            'Київ': 'kyiv',
            'Харків': 'kharkiv',
            'Дніпро': 'dnipro',
            'Одеса': 'odesa',
            'Львів': 'lviv',
            'Запоріжжя': 'zaporizhzhia',
            'Миколаїв': 'mykolaiv',
            'Хмельницький': 'khmelnytskyi',
            'Вінниця': 'vinnytsia',
            'Рівне': 'rivne',
            'Івано-Франківськ': 'ivano-frankivsk',
            'Черкаси': 'cherkasy',
        }
        slugs = {point.city_name: point.slug for point in BRANCH_POINTS}
        for name, slug in expected.items():
            self.assertEqual(slugs[name], slug)
        self.assertEqual(latin_slug('Запоріжжя'), 'zaporizhzhya')
        self.assertEqual(latin_slug('Вінниця'), 'vinnytsya')
        self.assertEqual(latin_slug('Івано-Франківськ'), 'ivano-frankivsk')
        for name in _NEW_CITY_NAMES:
            self.assertEqual(slugs[name], latin_slug(name))
        addresses = [point.address for point in BRANCH_POINTS]
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertIn('вул. Бульварно-Кудрявська, 32', addresses)
        self.assertIn('просп. Соборний, 153', addresses)
        self.assertIn('просп. Перемоги, 73', addresses)
        self.assertIn('вул. Ковельська, 3/3', addresses)
        self.assertIn('вул. Михайла Грушевського, 12', addresses)


class SyncBranchesTests(TestCase):
    def test_command_is_idempotent_and_keeps_eighteen_exact_rows(self):
        kyiv = City.objects.create(
            name='Київ',
            slug='kyiv',
            phone='+380441112233',
            is_active=True,
            sort_order=5,
        )
        branch = Branch.objects.create(
            city=kyiv,
            address='вул. Хрещатик, 1, Київ',
            hours='Пн–Нд, 8:00–21:00',
            phone='+380441112233',
            lat=Decimal('50.450000'),
            lng=Decimal('30.523000'),
            coords_manual=True,
            map_url=(
                'https://www.google.com/maps/search/?api=1&query='
                + quote_plus('вул. Хрещатик, 1, Київ')
            ),
            map_embed_url=(
                'https://www.google.com/maps/embed?pb=opaque-kyiv'
            ),
            is_active=False,
            sort_order=4,
        )
        BranchOpeningHours.objects.create(
            branch=branch,
            day_of_week=0,
            opens='08:00',
            closes='21:00',
        )
        kharkiv = City.objects.create(
            name='Харків',
            slug='kharkiv',
            phone='+38057777',
            is_active=True,
        )
        first = Branch.objects.create(
            city=kharkiv,
            address='вул. Сумська, 10, Харків',
            hours='як було',
            phone='+38057777',
            is_active=True,
        )
        poltava = City.objects.create(
            name='Полтава',
            slug='poltava',
            phone='+38053222',
            is_active=True,
        )
        removed = Branch.objects.create(
            city=poltava,
            address='вул. Хрещатик, 1, Київ',
            hours='графік полтави',
            phone='+38053222',
            is_active=True,
        )
        empty = City.objects.create(name='Порожнє', slug='empty-city', is_active=True)
        removed_pk = removed.pk
        before_ids = set(Branch.objects.values_list('pk', flat=True))

        report = apply_branch_catalog(apps, dry_run=False)
        self.assertTrue(report.changed)
        self.assertIn(removed_pk, set(Branch.objects.values_list('pk', flat=True)))
        self.assertTrue(before_ids <= set(Branch.objects.values_list('pk', flat=True)))
        removed.refresh_from_db()
        self.assertFalse(removed.is_active)
        self.assertEqual(removed.address, 'вул. Хрещатик, 1, Київ')
        self.assertEqual(removed.phone, '+38053222')
        self.assertEqual(removed.hours, 'графік полтави')
        poltava.refresh_from_db()
        empty.refresh_from_db()
        self.assertFalse(poltava.is_active)
        self.assertFalse(empty.is_active)
        self.assertEqual(report.city_visibility, 'is_active')
        self.assertEqual(report.branch_visibility, 'is_active')

        branch.refresh_from_db()
        self.assertEqual(branch.address, 'вул. Бульварно-Кудрявська, 32')
        self.assertEqual(branch.phone, '+380441112233')
        self.assertEqual(branch.hours, 'Пн–Нд, 8:00–21:00')
        self.assertIsNone(branch.lat)
        self.assertIsNone(branch.lng)
        self.assertFalse(branch.coords_manual)
        self.assertEqual(branch.map_url, '')
        self.assertEqual(
            branch.map_embed_url,
            'https://www.google.com/maps/embed?pb=opaque-kyiv',
        )
        self.assertTrue(branch.is_active)
        self.assertEqual(
            BranchOpeningHours.objects.filter(branch=branch).count(),
            1,
        )
        kyiv.refresh_from_db()
        self.assertEqual(kyiv.phone, '+380441112233')
        self.assertTrue(kyiv.is_active)

        first.refresh_from_db()
        self.assertEqual(first.address, 'вул. Кацарська, 36/38')
        self.assertEqual(first.phone, '+38057777')
        self.assertEqual(first.hours, 'як було')
        self.assertEqual(first.name, '')
        second = kharkiv.branches.get(name='Барабашово')
        self.assertEqual(second.address, 'метро Академіка Барабашова')
        self.assertEqual(second.phone, '')
        self.assertEqual(second.hours, '')
        self.assertTrue(second.is_active)
        self.assertIsNone(second.lat)
        self.assertIsNone(second.lng)

        active = list(
            Branch.objects.filter(is_active=True)
            .select_related('city')
            .order_by('city__sort_order', 'sort_order', 'id'),
        )
        self.assertEqual(len(active), 18)
        expected = []
        for slug, _points in points_by_slug():
            expected.extend(item for item in BRANCH_POINTS if item.slug == slug)
        self.assertEqual(
            [(row.city.slug, row.address, row.name) for row in active],
            [(item.slug, item.address, item.branch_name) for item in expected],
        )
        lutsk = City.objects.get(slug='lutsk')
        self.assertEqual(lutsk.name, 'Луцьк')
        self.assertEqual(lutsk.name_mode, 'Луцьк')
        self.assertEqual(lutsk.phone, '')
        self.assertEqual(lutsk.name_in, 'у Луцьку')
        self.assertEqual(
            Branch.objects.filter(is_active=True).count(),
            18,
        )
        self.assertEqual(City.objects.filter(is_active=True).count(), 17)

        again = apply_branch_catalog(apps, dry_run=False)
        self.assertEqual(again.lines, [])
        self.assertFalse(again.changed)
        self.assertEqual(Branch.objects.filter(is_active=True).count(), 18)
        self.assertEqual(Branch.objects.filter(pk=removed_pk).count(), 1)
        stdout = StringIO()
        call_command('sync_branches', stdout=stdout)
        self.assertIn('Без змін.', stdout.getvalue())

    def test_dry_run_writes_nothing(self):
        city = City.objects.create(name='Полтава', slug='poltava', is_active=True)
        branch = Branch.objects.create(
            city=city,
            address='вул. Хрещатик, 1, Київ',
            phone='111',
            hours='9-18',
            is_active=True,
        )
        before = _snapshot()
        report = apply_branch_catalog(apps, dry_run=True)
        self.assertEqual(_snapshot(), before)
        self.assertTrue(any(line.startswith('- відділення') for line in report.lines))
        self.assertTrue(any('Луцьк' in line for line in report.lines))
        stdout = StringIO()
        call_command('sync_branches', '--dry-run', stdout=stdout)
        text = stdout.getvalue()
        self.assertIn('Режим перегляду, базу не змінено.', text)
        self.assertIn('вул. Бульварно-Кудрявська, 32', text)
        self.assertEqual(_snapshot(), before)
        branch.refresh_from_db()
        self.assertTrue(branch.is_active)
        self.assertFalse(City.objects.filter(slug='lutsk').exists())

    def test_same_address_keeps_coords_and_custom_maps(self):
        lviv = City.objects.create(name='Львів', slug='lviv', phone='380')
        branch = Branch.objects.create(
            city=lviv,
            address='вул.  Степана Бандери,   35',
            hours='10-19',
            phone='380',
            lat=Decimal('49.841900'),
            lng=Decimal('24.031500'),
            coords_manual=True,
            map_url='https://maps.example/custom-pin',
            map_embed_url='https://www.google.com/maps/embed?pb=keep',
        )
        named = City.objects.create(name='Луцьк', slug='luck-legacy', phone='222')
        legacy = Branch.objects.create(
            city=named,
            address='стара',
            phone='222',
            hours='8-20',
        )
        apply_branch_catalog(apps, dry_run=False)
        branch.refresh_from_db()
        self.assertEqual(branch.address, 'вул. Степана Бандери, 35')
        self.assertEqual(branch.lat, Decimal('49.841900'))
        self.assertEqual(branch.lng, Decimal('24.031500'))
        self.assertTrue(branch.coords_manual)
        self.assertEqual(branch.map_url, 'https://maps.example/custom-pin')
        self.assertEqual(branch.map_embed_url, 'https://www.google.com/maps/embed?pb=keep')
        self.assertEqual(branch.phone, '380')
        self.assertEqual(branch.hours, '10-19')
        self.assertFalse(City.objects.filter(slug='lutsk').exists())
        named.refresh_from_db()
        legacy.refresh_from_db()
        self.assertEqual(named.slug, 'luck-legacy')
        self.assertEqual(named.phone, '222')
        self.assertEqual(legacy.address, 'вул. Ковельська, 3/3')
        self.assertEqual(legacy.phone, '222')
        self.assertEqual(legacy.hours, '8-20')

    def test_contacts_and_jsonld_use_barabashovo_label(self):
        apply_branch_catalog(apps, dry_run=False)
        contacts = self.client.get('/kontakty/')
        self.assertEqual(contacts.status_code, 200)
        self.assertContains(contacts, 'Харків «Барабашово»')
        self.assertContains(contacts, 'метро Академіка Барабашова')
        self.assertContains(contacts, 'вул. Кацарська, 36/38')
        page = self.client.get('/mista/kharkiv/')
        self.assertContains(page, '«Барабашово»')
        self.assertContains(page, 'метро Академіка Барабашова')
        home = self.client.get('/').content.decode()
        self.assertIn('Харків «Барабашово»', home)
        self.assertIn('метро Академіка Барабашова', home)

    def test_data_migration_is_idempotent_and_tests_skip_it(self):
        migration = importlib.import_module(
            'src.network.migrations.0015_sync_real_branches',
        )
        City.objects.create(name='Зайве', slug='extra-city', is_active=True)
        with override_settings(SYNC_BRANCHES_ON_MIGRATE=False):
            migration.sync_real_branches(apps, None)
        self.assertFalse(City.objects.filter(slug='kyiv').exists())
        self.assertTrue(City.objects.filter(slug='extra-city', is_active=True).exists())
        with override_settings(SYNC_BRANCHES_ON_MIGRATE=True):
            migration.sync_real_branches(apps, None)
            migration.sync_real_branches(apps, None)
        self.assertEqual(Branch.objects.filter(is_active=True).count(), 18)
        extra = City.objects.get(slug='extra-city')
        self.assertFalse(extra.is_active)
        self.assertEqual(
            Branch.objects.get(city__slug='odesa', is_active=True).address,
            'вул. Рішельєвська, 54',
        )

    def test_migrate_env_zero_skips_sync(self):
        migration = importlib.import_module(
            'src.network.migrations.0015_sync_real_branches',
        )
        with override_settings(SYNC_BRANCHES_ON_MIGRATE=True):
            with patch.dict(os.environ, {'SYNC_BRANCHES_ON_MIGRATE': '0'}):
                migration.sync_real_branches(apps, None)
        self.assertFalse(City.objects.filter(slug='kyiv').exists())
