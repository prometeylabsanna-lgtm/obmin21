from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0003_cms_page_sections'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='phone',
            field=models.CharField(blank=True, max_length=32, verbose_name='Телефон'),
        ),
    ]
