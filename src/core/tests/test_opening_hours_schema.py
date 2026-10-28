import json
import re
from datetime import time

from django.test import TestCase

from src.core.tests.test_eo_default_mode import forced_exchange_client
from src.core.tests.test_seo_schema import _business
from src.network.hours import SCHEMA_DAYS
from src.network.models import Branch, BranchOpeningHours, City

_WEEK = 'Пн–Нд, 8:00–21:00'
_SPLIT = 'Пн–Пт 09:00–19:00, Сб 10:00–16:00'


def _department(html, address):
    departments = _business(html)['department']
    return next(
        node for node in departments
        if node.get('address', {}).get('streetAddress') == address
    )


class OpeningHoursSchemaTests(TestCase):
    def test_json_ld_uses_rows_then_text_and_keeps_hours_string(self):
        city = City.objects.create(name='Київ', slug='kyiv-hours-schema')
        parsed = Branch.objects.create(
            city=city,
            address='вул. Тестова, 1',
            hours=_WEEK,
            phone='+380441110011',
            is_active=True,
            sort_order=1,
        )
        structured = Branch.objects.create(
            city=city,
            address='вул. Тестова, 2',
            hours=_SPLIT,
            is_active=True,
            sort_order=2,
        )
        BranchOpeningHours.objects.create(
            branch=structured,
            day_of_week=0,
            opens=time(10, 0),
            closes=time(12, 0),
            is_closed=False,
        )
        BranchOpeningHours.objects.create(
            branch=structured,
            day_of_week=5,
            opens=time(10, 0),
            closes=time(12, 0),
            is_closed=True,
        )
        BranchOpeningHours.objects.create(
            branch=structured,
            day_of_week=6,
            opens=time(11, 0),
            closes=time(13, 0),
            is_closed=False,
        )
        unknown = Branch.objects.create(
            city=city,
            address='вул. Тестова, 3',
            hours='Щодня 8:00-21:00',
            is_active=True,
            sort_order=3,
        )
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                with forced_exchange_client(enabled) as client:
                    html = client.get('/').content.decode()
                raw = re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    html,
                    re.S,
                ).group(1)
                payload = json.loads(raw)
                self.assertIn('openingHoursSpecification', json.dumps(payload))
                from_text = _department(html, parsed.address)
                self.assertEqual(from_text['openingHours'], _WEEK)
                self.assertEqual(from_text['openingHoursSpecification'], [{
                    '@type': 'OpeningHoursSpecification',
                    'dayOfWeek': list(SCHEMA_DAYS),
                    'opens': '08:00',
                    'closes': '21:00',
                }])
                from_rows = _department(html, structured.address)
                self.assertEqual(from_rows['openingHours'], _SPLIT)
                self.assertEqual(from_rows['openingHoursSpecification'], [
                    {
                        '@type': 'OpeningHoursSpecification',
                        'dayOfWeek': [SCHEMA_DAYS[0]],
                        'opens': '10:00',
                        'closes': '12:00',
                    },
                    {
                        '@type': 'OpeningHoursSpecification',
                        'dayOfWeek': [SCHEMA_DAYS[6]],
                        'opens': '11:00',
                        'closes': '13:00',
                    },
                ])
                self.assertNotIn(SCHEMA_DAYS[5], json.dumps(
                    from_rows['openingHoursSpecification'],
                ))
                dirty = _department(html, unknown.address)
                self.assertEqual(dirty['openingHours'], 'Щодня 8:00-21:00')
                self.assertNotIn('openingHoursSpecification', dirty)
