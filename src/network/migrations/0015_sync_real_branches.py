from django.db import migrations


def sync_enabled():
    import os

    from django.conf import settings

    raw = os.environ.get('SYNC_BRANCHES_ON_MIGRATE')
    if raw is not None and raw.strip():
        return raw.strip().lower() not in {'0', 'false', 'no', 'off'}
    return bool(getattr(settings, 'SYNC_BRANCHES_ON_MIGRATE', True))


def sync_real_branches(apps, schema_editor):
    if not sync_enabled():
        return
    from src.network.branch_sync import apply_branch_catalog

    apply_branch_catalog(apps, dry_run=False)


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0014_branch_name'),
    ]

    operations = [
        migrations.RunPython(sync_real_branches, migrations.RunPython.noop),
    ]
