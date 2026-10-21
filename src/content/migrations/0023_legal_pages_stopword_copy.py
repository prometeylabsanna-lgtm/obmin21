from django.db import migrations


def clean_legal_pages(apps, schema_editor):
    from src.content.legal_copy import apply_legal_replacements

    apply_legal_replacements(apps, schema_editor)


def noop_legal_pages(apps, schema_editor):
    from src.content.stage3_fill import noop_reverse

    return noop_reverse(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0022_servicespage_hero_text_mode'),
    ]

    operations = [
        migrations.RunPython(clean_legal_pages, noop_legal_pages),
    ]
