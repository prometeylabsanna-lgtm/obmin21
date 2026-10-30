from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0015_sync_real_branches'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='banner_suffix',
            field=models.CharField(
                blank=True,
                default='за вигідним курсом',
                help_text='Порожнє — після назви міста нічого не буде.',
                max_length=80,
                verbose_name='Текст після назви міста',
            ),
        ),
    ]
