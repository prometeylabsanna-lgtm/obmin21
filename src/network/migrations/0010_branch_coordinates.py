"""Intentionally empty. Coordinates come from admin geocoding."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0009_clear_placeholder_branch_coords'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
