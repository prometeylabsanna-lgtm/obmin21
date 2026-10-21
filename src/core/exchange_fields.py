from django.core.exceptions import FieldDoesNotExist
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


def _model_has_field(instance, name):
    meta = getattr(instance, '_meta', None)
    if meta is None:
        return False
    try:
        meta.get_field(name)
    except FieldDoesNotExist:
        return False
    return True


def resolved_text(instance, name, default=''):
    """Поле запису, або його варіант для режиму, коли режим увімкнено.

    Порожнє основне поле замінюється на ``default``.
    Порожнє поле режиму лишається порожнім.
    """
    from src.core.exchange_mode import exchange_only

    mode_name = f'{name}_mode'
    if exchange_only() and _model_has_field(instance, mode_name):
        return (getattr(instance, mode_name) or '').strip()
    raw = getattr(instance, name, '') or ''
    if isinstance(raw, str) and raw.strip():
        return raw
    return default
