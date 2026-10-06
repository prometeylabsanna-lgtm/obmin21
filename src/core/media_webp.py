from __future__ import annotations

from io import BytesIO
import os

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db.models import ImageField
from PIL import Image, ImageOps, UnidentifiedImageError

from src.core.admin_guidelines import image_limit

_OK_FORMATS = frozenset({'JPEG', 'PNG', 'WEBP', 'GIF'})


def image_file_validator(field_name: str):
    limit = image_limit(field_name)

    def check(value):
        if not value:
            return
        upload = _as_upload(value)
        if upload is None:
            return
        size = getattr(upload, 'size', None)
        if size and size > limit.max_mb * 1024 * 1024:
            mb = size / (1024 * 1024)
            raise ValidationError(
                f'Файл завеликий: {mb:.1f} МБ. Потрібно до {limit.max_mb:g} МБ.',
            )
        try:
            upload.seek(0)
            img = Image.open(upload)
            img.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError('Це не картинка. Потрібен JPG, PNG або WebP.') from None
        upload.seek(0)
        try:
            img = Image.open(upload)
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError('Це не картинка. Потрібен JPG, PNG або WebP.') from None
        fmt = (img.format or '').upper()
        if fmt not in _OK_FORMATS:
            raise ValidationError('Це не картинка. Потрібен JPG, PNG або WebP.')
        width, height = img.size
        if width > limit.max_w * 2 or height > limit.max_h * 2:
            raise ValidationError(
                f'Картинка завелика: {width}×{height}. '
                f'Потрібно до {limit.max_w}×{limit.max_h}.',
            )
        upload.seek(0)

    check.__name__ = 'cms_image_limit'
    return check


def convert_instance_images(obj) -> None:
    for field in obj._meta.fields:
        if not isinstance(field, ImageField):
            continue
        stored = getattr(obj, field.name)
        if not stored or getattr(stored, '_committed', True):
            continue
        converted = to_webp(stored.file, field.name, stored.name)
        if converted is None:
            continue
        stored.save(converted.name, converted, save=False)


def to_webp(upload, field_name: str, original_name: str = '') -> ContentFile | None:
    if upload is None:
        return None
    limit = image_limit(field_name)
    try:
        upload.seek(0)
        img = Image.open(upload)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    img = ImageOps.exif_transpose(img)
    if img.mode in ('P', 'LA'):
        img = img.convert('RGBA')
    elif img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    img = _fit(img, limit.max_w, limit.max_h)
    buffer = BytesIO()
    img.save(buffer, format='WEBP', quality=82, method=4)
    buffer.seek(0)
    stem = os.path.splitext(os.path.basename(original_name or getattr(upload, 'name', 'image')))[0]
    stem = stem or 'image'
    return ContentFile(buffer.read(), name=f'{stem}.webp')


def _fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    width, height = img.size
    if width <= max_w and height <= max_h:
        return img
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img


def _as_upload(value):
    if isinstance(value, UploadedFile):
        return value
    inner = getattr(value, 'file', None)
    if isinstance(inner, UploadedFile):
        return inner
    nested = getattr(inner, 'file', None)
    if isinstance(nested, UploadedFile):
        return nested
    return None
