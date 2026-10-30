import importlib
from datetime import time

from django.apps import apps
from django.db import migrations
from django.test import SimpleTestCase, TestCase
from django.test.utils import captured_stdout

from src.network import hours as hours_module
from src.network.hours import (
    SCHEMA_DAYS,
    format_hours,
    open_slots,
    opening_hours_specification,
    parse_hours,
)
from src.network.models import Branch, BranchOpeningHours, City

_migration = importlib.import_module(
    'src.network.migrations.0012_fill_branch_opening_hours',
)
fill_branch_opening_hours = _migration.fill_branch_opening_hours


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _Row:
    def __init__(self, day, opens, closes, is_closed=False):
        self.day_of_week = day
        self.opens = opens
        self.closes = closes
        self.is_closed = is_closed


class _Branch:
    def __init__(self, hours, rows=None):
        self.hours = hours
        if rows is not None:
            self.opening_hours = _Rows(rows)


class ParseHoursTests(SimpleTestCase):
    def test_week_and_split_groups(self):
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

    def test_hyphen_spaces_case_and_single_day(self):
        self.assertEqual(
            parse_hours('пн - нд , 8:00 - 21:00'),
            [(day, time(8, 0), time(21, 0)) for day in range(7)],
        )
        self.assertEqual(
            parse_hours('Пн-Пт 9:05-18:30, Сб 10:00-16:00'),
            [(day, time(9, 5), time(18, 30)) for day in range(5)]
            + [(5, time(10, 0), time(16, 0))],
        )
        self.assertEqual(
            parse_hours('Ср 8:00–12:00'),
            [(2, time(8, 0), time(12, 0))],
        )
        self.assertEqual(
            parse_hours('  Пн–Нд, 8:00–21:00  '),
            [(day, time(8, 0), time(21, 0)) for day in range(7)],
        )

    def test_unparseable_and_closed_by_omission(self):
        for text in (
            '',
            '   ',
            None,
            'Щодня 8:00-21:00',
            'swift 9-18',
            '9-18',
            '8:00–21:00',
            'Пн 8:00–21:00 extra',
            'Пн–Пт 09:00–19:00, Ср 10:00–12:00',
            'Нд–Пн 10:00-12:00',
            'Пн 21:00–08:00',
            'Пн 10:00–10:00',
            'Пн 8:60–9:00',
            'Пн 8:00–24:00',
            'Пн, Вт 09:00-18:00',
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse_hours(text))


class OpeningHoursSpecificationTests(SimpleTestCase):
    def test_groups_same_times_and_skips_closed(self):
        slots = (
            [(day, time(8, 0), time(21, 0)) for day in range(5)]
            + [(5, time(10, 0), time(16, 0))]
            + [(6, time(8, 0), time(21, 0))]
        )
        spec = opening_hours_specification(slots)
        self.assertEqual(spec, [
            {
                '@type': 'OpeningHoursSpecification',
                'dayOfWeek': [SCHEMA_DAYS[day] for day in (0, 1, 2, 3, 4, 6)],
                'opens': '08:00',
                'closes': '21:00',
            },
            {
                '@type': 'OpeningHoursSpecification',
                'dayOfWeek': [SCHEMA_DAYS[5]],
                'opens': '10:00',
                'closes': '16:00',
            },
        ])
        self.assertEqual(opening_hours_specification([]), [])
        self.assertEqual(opening_hours_specification(None), [])

    def test_open_slots_use_hours_text_only(self):
        text = 'Пн–Нд, 8:00–21:00'
        plain = _Branch(text)
        self.assertEqual(len(open_slots(plain)), 7)
        self.assertIsNone(open_slots(_Branch('Щодня 8:00-21:00')))
        ignored_rows = _Branch(text, rows=[
            _Row(0, time(10, 0), time(12, 0)),
        ])
        self.assertEqual(
            open_slots(ignored_rows),
            [(day, time(8, 0), time(21, 0)) for day in range(7)],
        )


class FillOpeningHoursMigrationTests(TestCase):
    def test_migration_follows_schema_and_reverse_is_noop(self):
        self.assertEqual(
            _migration.Migration.dependencies,
            [('network', '0011_branch_opening_hours')],
        )
        operation = _migration.Migration.operations[0]
        self.assertIs(operation.code, fill_branch_opening_hours)
        self.assertIs(operation.reverse_code, migrations.RunPython.noop)

    def test_fills_rows_logs_unparseable_and_keeps_text(self):
        city = City.objects.create(name='Харків', slug='kharkiv-hours')
        parsed = Branch.objects.create(
            city=city,
            address='вул. Сумська, 10, Харків',
            hours='Пн–Пт 09:00–19:00, Сб 10:00–16:00',
            phone='111',
        )
        unknown = Branch.objects.create(
            city=city,
            address='без графіка',
            hours='Щодня 8:00-21:00',
            phone='222',
        )
        empty = Branch.objects.create(
            city=city,
            address='порожній графік',
            hours='   ',
        )
        before = {
            branch.pk: (branch.hours, branch.phone, branch.address)
            for branch in (parsed, unknown, empty)
        }

        with captured_stdout() as stdout:
            with self.assertLogs(_migration.logger.name, level='WARNING') as logs:
                fill_branch_opening_hours(apps, None)
                fill_branch_opening_hours(apps, None)
        migrations.RunPython.noop(apps, None)

        output = stdout.getvalue()
        self.assertEqual(output.count('Нерозпізнаний графік'), 2)
        self.assertIn('Щодня 8:00-21:00', output)
        self.assertIn(str(unknown.pk), output)
        self.assertTrue(any('Щодня 8:00-21:00' in line for line in logs.output))
        self.assertEqual(
            BranchOpeningHours.objects.filter(branch=unknown).count(),
            0,
        )
        self.assertEqual(
            BranchOpeningHours.objects.filter(branch=empty).count(),
            0,
        )
        rows = list(
            BranchOpeningHours.objects.filter(branch=parsed).order_by('day_of_week')
        )
        self.assertEqual(len(rows), 7)
        for row in rows[:5]:
            self.assertFalse(row.is_closed)
            self.assertEqual(row.opens, time(9, 0))
            self.assertEqual(row.closes, time(19, 0))
        self.assertEqual(rows[5].opens, time(10, 0))
        self.assertEqual(rows[5].closes, time(16, 0))
        self.assertFalse(rows[5].is_closed)
        self.assertTrue(rows[6].is_closed)
        self.assertIsNone(rows[6].opens)
        self.assertIsNone(rows[6].closes)
        self.assertEqual(
            BranchOpeningHours.objects.filter(branch=parsed).count(),
            7,
        )
        for branch in (parsed, unknown, empty):
            branch.refresh_from_db()
            self.assertEqual(
                (branch.hours, branch.phone, branch.address),
                before[branch.pk],
            )


def _rows_for(text):
    slots = parse_hours(text)
    by_day = {day: (opens, closes) for day, opens, closes in slots}
    rows = []
    for day in range(7):
        if day in by_day:
            opens, closes = by_day[day]
            rows.append(_Row(day, opens, closes, False))
        else:
            rows.append(_Row(day, None, None, True))
    return rows


class FormatHoursTests(SimpleTestCase):
    def test_round_trip_of_both_prod_texts(self):
        for text in (
            'Пн–Нд, 8:00–21:00',
            'Пн–Пт 09:00–19:00, Сб 10:00–16:00',
        ):
            with self.subTest(text=text):
                rows = _rows_for(text)
                self.assertEqual(format_hours(rows), text)
                open_only = [
                    _Row(day, opens, closes)
                    for day, opens, closes in parse_hours(text)
                ]
                self.assertEqual(format_hours(open_only), text)
                self.assertEqual(parse_hours(format_hours(rows)), parse_hours(text))

    def test_single_group_drops_open_zero_and_keeps_close(self):
        self.assertEqual(
            format_hours([_Row(0, time(8, 0), time(9, 5))]),
            'Пн, 8:00–09:05',
        )

    def test_gap_keeps_groups_separate_and_pads_hours(self):
        rows = [
            _Row(0, time(8, 0), time(21, 0)),
            _Row(2, time(8, 0), time(21, 0)),
        ]
        self.assertEqual(format_hours(rows), 'Пн 08:00–21:00, Ср 08:00–21:00')

    def test_closed_and_empty_produce_blank(self):
        self.assertEqual(format_hours([]), '')
        self.assertEqual(format_hours(None), '')
        self.assertEqual(format_hours([_Row(0, None, None, True)]), '')
        self.assertIn('Пн–Нд, 8:00–21:00', hours_module.__doc__)
        self.assertIn('Пн–Пт 09:00–19:00, Сб 10:00–16:00', hours_module.__doc__)


class HoursDisplayTests(TestCase):
    def test_hours_display_uses_editable_text(self):
        city = City.objects.create(name='Львів', slug='lviv-display')
        branch = Branch.objects.create(
            city=city,
            address='пл. Ринок, 1',
            hours='Пн–Нд, 8:00–21:00',
        )
        self.assertEqual(branch.hours_display, 'Пн–Нд, 8:00–21:00')
        for day in range(7):
            BranchOpeningHours.objects.create(
                branch=branch,
                day_of_week=day,
                opens=time(10, 0),
                closes=time(12, 0),
            )
        self.assertEqual(branch.hours_display, 'Пн–Нд, 8:00–21:00')
        branch.hours = 'Пн–Пт 09:00–19:00, Сб 10:00–16:00'
        branch.save(update_fields=['hours'])
        self.assertEqual(
            branch.hours_display,
            'Пн–Пт 09:00–19:00, Сб 10:00–16:00',
        )
        empty = Branch.objects.create(city=city, address='пл. Ринок, 2', hours='')
        self.assertEqual(empty.hours_display, '')
