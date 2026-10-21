from django.db import migrations


def fill_cmp_home_leads(apps, schema_editor):
    from src.content.stage3_fill import fill_cmp_and_home_lead_mode

    fill_cmp_and_home_lead_mode(apps, schema_editor)


def noop_cmp_home_leads(apps, schema_editor):
    from src.content.stage3_fill import noop_reverse

    return noop_reverse(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0023_legal_pages_stopword_copy'),
    ]

    operations = [
        migrations.RunPython(fill_cmp_home_leads, noop_cmp_home_leads),
    ]
