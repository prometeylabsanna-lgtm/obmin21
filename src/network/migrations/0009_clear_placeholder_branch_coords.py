from decimal import Decimal

from django.db import migrations

_QUANT = Decimal('0.000001')
_LAT = Decimal('50.4472').quantize(_QUANT)
_LNG = Decimal('30.5215').quantize(_QUANT)


def _coord(value):
    if value is None:
        return None
    if isinstance(value, float):
        number = Decimal(str(value))
    else:
        number = Decimal(value)
    return number.quantize(_QUANT)


def is_placeholder_coords(lat, lng):
    return _coord(lat) == _LAT and _coord(lng) == _LNG


def clear_placeholder_coords(apps, schema_editor):
    """Ставить lat і lng у NULL лише для точної заглушки (50.4472, 30.5215)."""
    Branch = apps.get_model('network', 'Branch')
    matched = [
        branch.pk
        for branch in Branch.objects.all().iterator()
        if is_placeholder_coords(branch.lat, branch.lng)
    ]
    if matched:
        Branch.objects.filter(pk__in=matched).update(lat=None, lng=None)


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0008_branch_map_embed_url'),
    ]

    operations = [
        migrations.RunPython(clear_placeholder_coords, migrations.RunPython.noop),
    ]
