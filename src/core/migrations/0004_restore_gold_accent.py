from django.db import migrations

GOLD = '#ca8d42'
WRONG = frozenset({'#253855', '#4e7394'})


def forwards(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for obj in SiteSettings.objects.all():
        changed = False
        for field in ('header_color_accent', 'footer_color_accent'):
            if (getattr(obj, field) or '').lower() in WRONG:
                setattr(obj, field, GOLD)
                changed = True
        if changed:
            obj.save(update_fields=['header_color_accent', 'footer_color_accent'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_accent_253855'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
