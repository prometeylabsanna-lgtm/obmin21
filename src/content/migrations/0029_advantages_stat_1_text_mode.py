from django.db import migrations


def fill_stat_1_mode(apps, schema_editor):
    from src.content.advantages_mode_copy import fill_stat_1_text_mode

    fill_stat_1_text_mode(apps, schema_editor)


def noop_stat_1_mode(apps, schema_editor):
    from src.content.stage3_fill import noop_reverse

    return noop_reverse(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0028_advantages_page_mode_fields'),
    ]

    operations = [
        migrations.RunPython(fill_stat_1_mode, noop_stat_1_mode),
    ]
