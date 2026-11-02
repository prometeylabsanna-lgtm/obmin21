import hashlib

BANNER_STAMP_FIELDS = (
    'banner_image',
    'banner_title',
    'banner_title_mode',
    'banner_suffix',
    'banner_suffix_mode',
    'banner_text',
    'banner_text_mode',
    'banner_button',
    'banner_button_mode',
)


def _field_token(value):
    if value is None:
        return ''
    name = getattr(value, 'name', None)
    if name is not None:
        return str(name)
    return str(value)


def city_banner_stamp(city):
    parts = []
    for name in BANNER_STAMP_FIELDS:
        parts.append(f'{name}={_field_token(getattr(city, name, ""))!r}')
    payload = '\n'.join(parts).encode()
    return hashlib.sha256(payload).hexdigest()
