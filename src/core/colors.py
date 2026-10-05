from django.core.validators import RegexValidator

hex_color_validator = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Оберіть колір у палітрі.',
)

COLOR_HELP = 'Натисніть квадратик, щоб обрати колір. Зміна з’явиться на сайті після збереження.'
ACCENT_DEFAULT = '#4e7394'
ACCENT_HOVER_DEFAULT = '#3e5d78'
