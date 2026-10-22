from django.db import migrations


def fill_home_seo_and_articles_lead(apps, schema_editor):
    from src.content.stage3_fill import fill_articles_lead, fill_home_seo_mode

    fill_home_seo_mode(apps, schema_editor)
    fill_articles_lead(apps, schema_editor)


def noop_home_seo_and_articles_lead(apps, schema_editor):
    from src.content.stage3_fill import noop_reverse

    return noop_reverse(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0024_cmp_and_home_lead_mode'),
    ]

    operations = [
        migrations.RunPython(
            fill_home_seo_and_articles_lead,
            noop_home_seo_and_articles_lead,
        ),
    ]
