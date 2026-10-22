from django.db import models

MODE_FIELD_HELP = (
    'Показується, коли увімкнено "Лише обмін"; порожнє — блок не показується.'
)

EXCHANGE_SAFE_VERBOSE = 'Показувати в режимі «Лише обмін»'
EXCHANGE_SAFE_HELP = (
    'У режимі «Лише обмін» на сайті лишаються лише позначені записи. '
    'Новий запис створюється без галочки і в цьому режимі не показується. '
    'Коли режим вимкнено, галочка ні на що не впливає.'
)
EXCHANGE_SAFE_CURRENCY_HELP = 'показувати в режимі «Лише обмін валют»'


def mode_char(label, max_length):
    return models.CharField(
        label,
        max_length=max_length,
        blank=True,
        help_text=MODE_FIELD_HELP,
    )


def mode_text(label):
    return models.TextField(label, blank=True, help_text=MODE_FIELD_HELP)


def mode_image(label, upload_to):
    return models.ImageField(
        label,
        upload_to=upload_to,
        blank=True,
        help_text=MODE_FIELD_HELP,
    )


def mode_json(label):
    return models.JSONField(
        label,
        blank=True,
        null=True,
        help_text=MODE_FIELD_HELP,
    )


def resolved_text(instance, name, default=''):
    """Поза режимом — непорожнє поле, інакше ``default``.

    У режимі делегує ``exchange_mode.mode_text``.
    """
    from src.core import exchange_mode

    if exchange_mode.exchange_only():
        return exchange_mode.mode_text(instance, name)
    raw = getattr(instance, name, '') or ''
    if isinstance(raw, str) and raw.strip():
        return raw
    return default
