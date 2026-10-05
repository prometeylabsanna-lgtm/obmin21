from django.core.validators import RegexValidator

hex_color_validator = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Оберіть колір у палітрі.',
)

COLOR_HELP = 'Натисніть квадратик, щоб обрати колір. Зміна з’явиться на сайті після збереження.'
ACCENT_DEFAULT = '#ca8d42'
ACCENT_HOVER_DEFAULT = '#b87b2c'
ACCENT_RGB_DEFAULT = '202, 141, 66'
LEGACY_ACCENTS = frozenset({'#253855', '#4e7394'})

UNFOLD_PRIMARY = {
    '50': '#fbf6ee',
    '100': '#f6ecd9',
    '200': '#eed7b0',
    '300': '#e4c07e',
    '400': '#d6a55a',
    '500': '#ca8d42',
    '600': '#ca8d42',
    '700': '#b87b2c',
    '800': '#8f5f22',
    '900': '#6b471c',
    '950': '#3d280f',
}

UNFOLD_BASE = {
    '50': '#ffffff',
    '100': '#f4f6f8',
    '200': '#e6ebf0',
    '300': '#c5d0de',
    '400': '#8a9bb0',
    '500': '#5a6f88',
    '600': '#3d5470',
    '700': '#1c3350',
    '800': '#0a2a4a',
    '900': '#052145',
    '950': '#031428',
}
