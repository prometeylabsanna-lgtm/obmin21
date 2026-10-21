from django.db import migrations, models


def invert_exchange_only(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for row in SiteSettings.objects.all():
        row.exchange_only = not row.exchange_only
        row.save(update_fields=['exchange_only'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_sitesettings_crypto_enabled'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sitesettings',
            old_name='crypto_enabled',
            new_name='exchange_only',
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='exchange_only',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Увімкнено — на сайті тимчасово лишається лише обмін валют. '
                    'Кнопка на цій сторінці вмикає і вимикає режим.'
                ),
                verbose_name='Лише обмін валют',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='exchange_only_since',
            field=models.DateTimeField(
                blank=True,
                help_text='Порожнє — режим вимкнено або час ще не зафіксовано.',
                null=True,
                verbose_name='Режим «Лише обмін» увімкнено з',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='hidden_page_status',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (503, '503 — тимчасово недоступно'),
                    (404, '404 — сторінку не знайдено'),
                ],
                default=503,
                help_text=(
                    '503 каже Google, що сторінка на паузі і її треба тримати в пошуку. '
                    '404 — якщо режим триває довше ніж один-два тижні.'
                ),
                verbose_name='Відповідь для прихованих сторінок',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='retry_after_seconds',
            field=models.PositiveIntegerField(
                default=86400,
                help_text='Скільки секунд зачекати перед повторним візитом. 86400 — одна доба.',
                verbose_name='Retry-After, секунд',
            ),
        ),
        migrations.RunPython(invert_exchange_only, invert_exchange_only),
    ]
