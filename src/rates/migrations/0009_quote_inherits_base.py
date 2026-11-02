from django.db import migrations, models


def fill_inherits_base(apps, schema_editor):
    from src.rates.base_rate import assign_inherits_base

    assign_inherits_base(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('rates', '0008_exchange_visibility_kind'),
    ]

    operations = [
        migrations.AddField(
            model_name='quote',
            name='inherits_base',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Лише для курсу міста. Увімкнено — на сайті купівля і продаж '
                    'беруться з базового курсу цієї пари. Вимкнено — свої числа міста.'
                ),
                verbose_name='Наслідує базовий курс',
            ),
        ),
        migrations.RunPython(fill_inherits_base, migrations.RunPython.noop),
    ]
