from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0007_restore_gold_accent'),
    ]

    operations = [
        migrations.RenameField(
            model_name='homepage',
            old_name='banner_exchange',
            new_name='promo_image',
        ),
        migrations.AlterField(
            model_name='homepage',
            name='promo_image',
            field=models.ImageField(
                blank=True,
                help_text='Блок «Вигідний курс на USD та EUR» на головній.',
                upload_to='home/',
                verbose_name='Фото',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='promo_kicker',
            field=models.CharField(default='USD та EUR', max_length=80, verbose_name='Підпис над заголовком'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='promo_title',
            field=models.CharField(default='Вигідний курс', max_length=120, verbose_name='Заголовок'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='promo_title_accent',
            field=models.CharField(default='USD та EUR', max_length=80, verbose_name='Акцент у заголовку'),
        ),
        migrations.AddField(
            model_name='homepage',
            name='promo_text',
            field=models.CharField(
                default='Обмінюйте валюту за актуальним курсом без зайвих кроків',
                max_length=240,
                verbose_name='Текст',
            ),
        ),
        migrations.AddField(
            model_name='homepage',
            name='promo_button',
            field=models.CharField(default='Обрати валюту', max_length=80, verbose_name='Текст кнопки'),
        ),
        migrations.RemoveField(
            model_name='homepage',
            name='banner_service',
        ),
        migrations.RemoveField(
            model_name='homepage',
            name='banner_cta',
        ),
        migrations.RemoveField(
            model_name='homepage',
            name='cta_title',
        ),
        migrations.AddField(
            model_name='servicespage',
            name='hero_image',
            field=models.ImageField(
                blank=True,
                help_text='Блок «Усі фінансові послуги в одному місці».',
                upload_to='services/',
                verbose_name='Фото',
            ),
        ),
        migrations.AddField(
            model_name='servicespage',
            name='hero_title',
            field=models.CharField(
                default='Усі фінансові послуги',
                max_length=120,
                verbose_name='Заголовок банера',
            ),
        ),
        migrations.AddField(
            model_name='servicespage',
            name='hero_title_accent',
            field=models.CharField(
                default='в одному місці',
                max_length=80,
                verbose_name='Акцент у заголовку',
            ),
        ),
        migrations.AddField(
            model_name='servicespage',
            name='hero_text',
            field=models.CharField(
                default='Обмін валют, криптовалюти, перекази та інвестиційне золото з фіксацією курсу онлайн.',
                max_length=320,
                verbose_name='Текст банера',
            ),
        ),
        migrations.AlterField(
            model_name='servicespage',
            name='title',
            field=models.CharField(default='Послуги', max_length=120, verbose_name='Заголовок сторінки'),
        ),
    ]
