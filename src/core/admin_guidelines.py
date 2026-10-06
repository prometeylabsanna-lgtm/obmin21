from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import ImageField

from src.core.plain_text import plain_text


@dataclass(frozen=True)
class ImageLimit:
    max_w: int
    max_h: int
    max_mb: float
    hint: str


@dataclass(frozen=True)
class TextLimit:
    max_chars: int
    hint: str


_IMAGE_BY_NAME = {
    'header_logo': ImageLimit(800, 400, 0.5, 'Логотип: до 800×400 і 0,5 МБ. JPG, PNG або WebP.'),
    'footer_logo': ImageLimit(800, 400, 0.5, 'Логотип: до 800×400 і 0,5 МБ. JPG, PNG або WebP.'),
    'flag_image': ImageLimit(256, 256, 0.2, 'Іконка: до 256×256 і 0,2 МБ. JPG, PNG або WebP.'),
    'banner_image': ImageLimit(1920, 1080, 2, 'Фото банера: до 1920×1080 і 2 МБ. JPG, PNG або WebP.'),
    'hero_banner': ImageLimit(1920, 1080, 2, 'Фото банера: до 1920×1080 і 2 МБ. JPG, PNG або WebP.'),
    'hero_image': ImageLimit(1920, 1080, 2, 'Фото банера: до 1920×1080 і 2 МБ. JPG, PNG або WebP.'),
    'why_banner': ImageLimit(1920, 1080, 2, 'Фото банера: до 1920×1080 і 2 МБ. JPG, PNG або WebP.'),
    'cover': ImageLimit(1600, 1000, 1.5, 'Обкладинка: до 1600×1000 і 1,5 МБ. JPG, PNG або WebP.'),
    'promo_image': ImageLimit(1600, 1200, 1.5, 'Картинка блоку: до 1600×1200 і 1,5 МБ. JPG, PNG або WebP.'),
    'hero_cards_image': ImageLimit(1200, 800, 1, 'Картинка: до 1200×800 і 1 МБ. JPG, PNG або WebP.'),
    'image': ImageLimit(1600, 1000, 1.5, 'Фото картки: до 1600×1000 і 1,5 МБ. JPG, PNG або WebP.'),
    'figure': ImageLimit(1200, 800, 1, 'Картинка: до 1200×800 і 1 МБ. JPG, PNG або WebP.'),
    'why_coins': ImageLimit(1600, 1600, 1.5, 'Картинка монет: до 1600×1600 і 1,5 МБ. JPG, PNG або WebP.'),
}

_IMAGE_DEFAULT = ImageLimit(
    1920,
    1920,
    2,
    'Картинка: до 1920×1920 і 2 МБ. JPG, PNG або WebP.',
)

_TEXT_BY_NAME = {
    'seo_title': TextLimit(70, 'До 70 символів — короткий заголовок для пошуку.'),
    'seo_description': TextLimit(160, 'До 160 символів — короткий опис для пошуку.'),
    'seo_block_title': TextLimit(80, 'До 80 символів.'),
}

_TEXT_BY_SUFFIX = (
    (('_kicker', '_btn', '_button', '_cta'), TextLimit(80, 'До 80 символів.')),
    (('_title', '_accent', '_name', '_give', '_get'), TextLimit(120, 'До 120 символів.')),
    (('_lead', '_hint'), TextLimit(400, 'До 400 символів, приблизно 5 рядків.')),
    (('_text', '_desc', 'short_desc'), TextLimit(500, 'До 500 символів, приблизно 7 рядків.')),
    (('_html', 'answer', 'body', 'faq', 'intro'), TextLimit(4000, 'До 4000 символів тексту.')),
)

_SKIP = frozenset({
    'slug',
    'password',
    'username',
    'email',
    'last_login',
    'date_joined',
    'id',
})
_COLOR_PREFIXES = ('color_', 'header_color_', 'footer_color_')
_IMAGE_NOTE = ' Після збереження стиснемо, щоб сайт відкривався швидше.'


def image_limit(field_name: str) -> ImageLimit:
    return _IMAGE_BY_NAME.get(field_name, _IMAGE_DEFAULT)


def image_help(field_name: str, existing: str = '') -> str:
    hint = image_limit(field_name).hint + _IMAGE_NOTE
    extra = (existing or '').strip()
    if extra and extra not in hint:
        return f'{hint} {extra}'
    return hint


_TEXT_EXACT = {
    'title': TextLimit(120, 'До 120 символів.'),
    'name': TextLimit(120, 'До 120 символів.'),
    'intro': TextLimit(4000, 'До 4000 символів тексту.'),
    'text': TextLimit(500, 'До 500 символів, приблизно 7 рядків.'),
    'body': TextLimit(8000, 'До 8000 символів тексту.'),
    'answer': TextLimit(4000, 'До 4000 символів тексту.'),
    'faq': TextLimit(4000, 'До 4000 символів тексту.'),
}


def text_limit_for(field_name: str, db_field, rich: bool = False) -> TextLimit | None:
    if field_name in _SKIP or field_name.startswith(_COLOR_PREFIXES):
        return None
    if field_name in _TEXT_BY_NAME:
        return _cap_to_model(_TEXT_BY_NAME[field_name], db_field)
    if field_name in _TEXT_EXACT:
        return _cap_to_model(_TEXT_EXACT[field_name], db_field)
    for suffixes, limit in _TEXT_BY_SUFFIX:
        if field_name in suffixes or field_name.endswith(suffixes):
            return _cap_to_model(limit, db_field)
    if rich:
        return TextLimit(4000, 'До 4000 символів тексту.')
    model_max = getattr(db_field, 'max_length', None)
    if model_max:
        return TextLimit(model_max, f'До {model_max} символів.')
    if db_field.get_internal_type() == 'TextField':
        return TextLimit(800, 'До 800 символів, приблизно 10 рядків.')
    return None


def _cap_to_model(limit: TextLimit, db_field) -> TextLimit:
    model_max = getattr(db_field, 'max_length', None)
    if model_max and model_max < limit.max_chars:
        return TextLimit(model_max, f'До {model_max} символів.')
    return limit


def text_help(limit: TextLimit, existing: str = '') -> str:
    extra = (existing or '').strip()
    if extra and extra not in limit.hint:
        return f'{limit.hint} {extra}'
    return limit.hint


def text_validator(limit: TextLimit, rich: bool):
    def check(value):
        raw = plain_text(value or '') if rich else (value or '')
        if len(raw) > limit.max_chars:
            raise ValidationError(
                f'Забагато тексту: {len(raw)} з {limit.max_chars} символів.',
            )
    check.__name__ = 'cms_text_limit'
    return check


def with_field_limits(db_field, kwargs: dict, *, rich: bool = False) -> dict:
    name = db_field.name
    if name in _SKIP or name.startswith(_COLOR_PREFIXES):
        return kwargs
    if isinstance(db_field, ImageField):
        from src.core.media_webp import image_file_validator
        kwargs['help_text'] = image_help(name, db_field.help_text)
        validators = list(kwargs.get('validators') or [])
        validators.append(image_file_validator(name))
        kwargs['validators'] = validators
        return kwargs
    if db_field.get_internal_type() not in ('CharField', 'TextField'):
        return kwargs
    limit = text_limit_for(name, db_field, rich=rich)
    if not limit:
        return kwargs
    kwargs['help_text'] = text_help(limit, db_field.help_text)
    validators = list(kwargs.get('validators') or [])
    validators.append(text_validator(limit, rich))
    kwargs['validators'] = validators
    return kwargs
