from django.core.validators import RegexValidator
from django.db import migrations, models

HELP = 'Натисніть квадратик, щоб обрати колір. Зміна з’явиться на сайті після збереження.'
HEX = RegexValidator(message='Оберіть колір у палітрі.', regex='^#[0-9A-Fa-f]{6}$')

PAGES = [
    'advantagespage',
    'blogpage',
    'citiespage',
    'contactspage',
    'cookiepage',
    'faqpage',
    'homepage',
    'offerpage',
    'privacypage',
    'ratespage',
    'reviewspage',
    'servicespage',
]


def _ops():
    ops = []
    for name in PAGES:
        ops.append(
            migrations.AlterField(
                model_name=name,
                name='color_accent',
                field=models.CharField(
                    default='#ca8d42',
                    help_text=HELP,
                    max_length=7,
                    validators=[HEX],
                    verbose_name='Колір акценту',
                ),
            ),
        )
        ops.append(
            migrations.AddField(
                model_name=name,
                name='color_highlight',
                field=models.CharField(
                    default='#b87b2c',
                    help_text=HELP,
                    max_length=7,
                    validators=[HEX],
                    verbose_name='Колір підсвітки',
                ),
            ),
        )
    return ops


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0013_seo_field_labels'),
    ]
    operations = _ops()
