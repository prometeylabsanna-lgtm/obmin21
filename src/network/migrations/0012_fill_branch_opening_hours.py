import logging

from django.db import migrations

from src.network.hours import parse_hours

logger = logging.getLogger(__name__)


def _report_unparseable(branch_id, text):
    message = f'Нерозпізнаний графік, відділення {branch_id}: {text}'
    logger.warning('%s', message)
    print(message)


def fill_branch_opening_hours(apps, schema_editor):
    """Створює рядки графіка з тексту. Нерозпізнаний текст лишає порожній набір рядків."""
    Branch = apps.get_model('network', 'Branch')
    Hours = apps.get_model('network', 'BranchOpeningHours')
    for branch in Branch.objects.all().iterator():
        text = branch.hours or ''
        parsed = parse_hours(text)
        if parsed is None:
            if str(text).strip():
                _report_unparseable(branch.pk, text)
            continue
        if Hours.objects.filter(branch_id=branch.pk).exists():
            continue
        open_days = {day: (opens, closes) for day, opens, closes in parsed}
        Hours.objects.bulk_create([
            Hours(
                branch_id=branch.pk,
                day_of_week=day,
                opens=open_days[day][0] if day in open_days else None,
                closes=open_days[day][1] if day in open_days else None,
                is_closed=day not in open_days,
            )
            for day in range(7)
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0011_branch_opening_hours'),
    ]

    operations = [
        migrations.RunPython(
            fill_branch_opening_hours,
            migrations.RunPython.noop,
        ),
    ]
