from django.db import migrations

from src.core.colors import ACCENT_DEFAULT, LEGACY_ACCENTS


def forwards(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for obj in SiteSettings.objects.all():
        changed = False
        for field in ('header_color_accent', 'footer_color_accent'):
            if (getattr(obj, field) or '').lower() in LEGACY_ACCENTS:
                setattr(obj, field, ACCENT_DEFAULT)
                changed = True
        if changed:
            obj.save(update_fields=['header_color_accent', 'footer_color_accent'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_admin_cms_theme'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
