from django.db import migrations

from src.core.colors import ACCENT_DEFAULT, LEGACY_ACCENTS

PAGE_MODELS = (
    'homepage',
    'ratespage',
    'contactspage',
    'servicespage',
    'advantagespage',
    'blogpage',
    'reviewspage',
    'citiespage',
    'faqpage',
    'privacypage',
    'offerpage',
    'cookiepage',
)


def forwards(apps, schema_editor):
    for name in PAGE_MODELS:
        model = apps.get_model('content', name)
        for obj in model.objects.all():
            if (obj.color_accent or '').lower() in LEGACY_ACCENTS:
                obj.color_accent = ACCENT_DEFAULT
                obj.save(update_fields=['color_accent'])


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0005_admin_cms_theme'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
