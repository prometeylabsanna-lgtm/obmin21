from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_faq_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='advantageitem',
            name='description',
            field=models.CharField(blank=True, max_length=320, verbose_name='Короткий опис'),
        ),
    ]
