import importlib
from datetime import time

from django.apps import apps
from django.db import migrations
from django.test import SimpleTestCase, TestCase

from src.network.hours import format_hours, parse_hours
from src.network.models import Branch, BranchOpeningHours, City

_coords = importlib.import_module(
    'src.network.migrations.0010_branch_coordinates',
)
_hours = importlib.import_module(
    'src.network.migrations.0012_fill_branch_opening_hours',
)
fill_branch_opening_hours = _hours.fill_branch_opening_hours

WEEK_HOURS = 'Пн–Нд, 8:00–21:00'
SPLIT_HOURS = 'Пн–Пт 09:00–19:00, Сб 10:00–16:00'
STUB_ADDRESS = 'вул. Хрещатик, 1, Київ'

PROD_BRANCHES = [
    ('kyiv', 'Київ', 'вул. Хрещатик, 1, Київ', 'Пн–Нд, 8:00–21:00'),
    ('kharkiv', 'Харків', 'вул. Сумська, 10, Харків', 'Пн–Нд, 8:00–21:00'),
    ('dnipro', 'Дніпро', 'пр. Яворницького, 50, Дніпро', 'Пн–Нд, 8:00–21:00'),
    ('odesa', 'Одеса', 'вул. Дерибасівська, 5, Одеса', 'Пн–Нд, 8:00–21:00'),
    ('lviv', 'Львів', 'пл. Ринок, 12, Львів', 'Пн–Нд, 8:00–21:00'),
    ('poltava', 'Полтава', 'вул. Хрещатик, 1, Київ', 'Пн–Пт 09:00–19:00, Сб 10:00–16:00'),
    ('sumy', 'Суми', 'вул. Хрещатик, 1, Київ', 'Пн–Пт 09:00–19:00, Сб 10:00–16:00'),
    ('zaporizhzhia', 'Запоріжжя', 'пр. Соборний, 100, Запоріжжя', 'Пн–Нд, 8:00–21:00'),
    ('vinnytsia', 'Вінниця', 'вул. Соборна, 30, Вінниця', 'Пн–Нд, 8:00–21:00'),
    (
        'ivano-frankivsk',
        'Івано-Франківськ',
        'вул. Хрещатик, 1, Київ',
        'Пн–Пт 09:00–19:00, Сб 10:00–16:00',
    ),
    ('mykolaiv', 'Миколаїв', 'вул. Соборна, 8, Миколаїв', 'Пн–Нд, 8:00–21:00'),
    (
        'kryvyi-rih',
        'Кривий Ріг',
        'вул. Хрещатик, 1, Київ',
        'Пн–Пт 09:00–19:00, Сб 10:00–16:00',
    ),
    (
        'khmelnytskyi',
        'Хмельницький',
        'вул. Проскурівська, 20, Хмельницький',
        'Пн–Нд, 8:00–21:00',
    ),
    ('rivne', 'Рівне', 'вул. Соборна, 15, Рівне', 'Пн–Нд, 8:00–21:00'),
    (
        'kropyvnytskyi',
        'Кропивницький',
        'вул. Хрещатик, 1, Київ',
        'Пн–Пт 09:00–19:00, Сб 10:00–16:00',
    ),
    ('cherkasy', 'Черкаси', 'бул. Шевченка, 200, Черкаси', 'Пн–Нд, 8:00–21:00'),
]


def _seed_prod_branches():
    branches = {}
    for slug, name, address, hours in PROD_BRANCHES:
        city = City.objects.create(name=name, slug=slug)
        branches[slug] = Branch.objects.create(
            city=city,
            address=address,
            hours=hours,
            lat=None,
            lng=None,
        )
    return branches


class ProdHoursParseTests(SimpleTestCase):
    def test_parse_hours_on_both_prod_strings(self):
        self.assertIn('\u2013', WEEK_HOURS)
        self.assertIn('\u2013', SPLIT_HOURS)
        week = parse_hours('Пн–Нд, 8:00–21:00')
        self.assertEqual(
            week,
            [(day, time(8, 0), time(21, 0)) for day in range(7)],
        )
        split = parse_hours('Пн–Пт 09:00–19:00, Сб 10:00–16:00')
        self.assertEqual(
            split,
            [(day, time(9, 0), time(19, 0)) for day in range(5)]
            + [(5, time(10, 0), time(16, 0))],
        )
        self.assertNotIn(6, [day for day, _opens, _closes in split])


class ProdBranchDataTests(TestCase):
    def test_coordinates_noop_and_opening_hours_from_prod_rows(self):
        self.assertEqual(len(PROD_BRANCHES), 16)
        self.assertEqual(
            {row[3] for row in PROD_BRANCHES},
            {WEEK_HOURS, SPLIT_HOURS},
        )

        branches = _seed_prod_branches()
        before = {}
        for slug, branch in branches.items():
            branch.refresh_from_db()
            before[slug] = (branch.address, branch.hours, branch.lat, branch.lng)
            self.assertIsNone(branch.lat, slug)
            self.assertIsNone(branch.lng, slug)
            if branch.address == STUB_ADDRESS and slug != 'kyiv':
                self.assertFalse(branch.has_real_address, slug)
            else:
                self.assertTrue(branch.has_real_address, slug)

        _coords.Migration.operations[0].code(apps, None)
        _coords.Migration.operations[0].code(apps, None)
        migrations.RunPython.noop(apps, None)

        for slug, branch in branches.items():
            branch.refresh_from_db()
            self.assertEqual(
                (branch.address, branch.hours, branch.lat, branch.lng),
                before[slug],
                slug,
            )
            self.assertIsNone(branch.lat, slug)
            self.assertIsNone(branch.lng, slug)

        fill_branch_opening_hours(apps, None)

        for slug, _name, _address, hours in PROD_BRANCHES:
            rows = list(
                BranchOpeningHours.objects.filter(
                    branch=branches[slug],
                ).order_by('day_of_week'),
            )
            self.assertEqual(len(rows), 7, slug)
            self.assertEqual(format_hours(rows), hours, slug)
            self.assertEqual(branches[slug].hours_display, hours, slug)
            if hours == 'Пн–Нд, 8:00–21:00':
                for row in rows:
                    self.assertFalse(row.is_closed, slug)
                    self.assertEqual(row.opens, time(8, 0), slug)
                    self.assertEqual(row.closes, time(21, 0), slug)
            else:
                self.assertEqual(hours, 'Пн–Пт 09:00–19:00, Сб 10:00–16:00')
                for row in rows[:5]:
                    self.assertFalse(row.is_closed, slug)
                    self.assertEqual(row.opens, time(9, 0), slug)
                    self.assertEqual(row.closes, time(19, 0), slug)
                self.assertFalse(rows[5].is_closed, slug)
                self.assertEqual(rows[5].opens, time(10, 0), slug)
                self.assertEqual(rows[5].closes, time(16, 0), slug)
                self.assertTrue(rows[6].is_closed, slug)
                self.assertIsNone(rows[6].opens, slug)
                self.assertIsNone(rows[6].closes, slug)
