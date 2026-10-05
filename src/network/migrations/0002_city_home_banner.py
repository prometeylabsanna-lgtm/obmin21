from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='banner_image',
            field=models.ImageField(
                blank=True,
                help_text='Якщо порожньо — стандартне фото міста.',
                upload_to='cities/',
                verbose_name='Фото банера на головній',
            ),
        ),
        migrations.AddField(
            model_name='city',
            name='banner_title',
            field=models.CharField(default='Обмін валют', max_length=80, verbose_name='Заголовок банера'),
        ),
        migrations.AddField(
            model_name='city',
            name='banner_suffix',
            field=models.CharField(
                default='за вигідним курсом',
                max_length=80,
                verbose_name='Текст після назви міста',
            ),
        ),
        migrations.AddField(
            model_name='city',
            name='banner_text',
            field=models.CharField(
                default='Фіксуйте курс онлайн та обмінюйте за вигідним курсом',
                max_length=240,
                verbose_name='Підпис на банері',
            ),
        ),
    ]
