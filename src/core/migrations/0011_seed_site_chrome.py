from django.db import migrations


def seed(apps, schema_editor):
    from src.core.site_chrome_seed import seed_site_chrome

    seed_site_chrome(apps)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0010_site_chrome_cms'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
