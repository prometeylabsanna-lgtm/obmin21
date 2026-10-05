from django.db import migrations

GOLD = '#ca8d42'
WRONG = frozenset({'#253855', '#4e7394'})

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
            if (obj.color_accent or '').lower() in WRONG:
                obj.color_accent = GOLD
                obj.save(update_fields=['color_accent'])


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0006_accent_253855'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
