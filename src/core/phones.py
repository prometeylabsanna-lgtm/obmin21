import re


def phone_digits(phone):
    return re.sub(r'\D+', '', phone or '')


def phone_tel(phone):
    digits = phone_digits(phone)
    if not digits:
        return ''
    if digits.startswith('380'):
        return f'+{digits}'
    if digits.startswith('0') and len(digits) == 10:
        return f'+38{digits}'
    if digits.startswith('38'):
        return f'+{digits}'
    return f'+{digits}'


def resolve_site_phone(request, settings):
    """Номер шапки і попапів: телефон міста, інакше загальний номер сайту."""
    city = getattr(request, 'city', None)
    display = ''
    if city is not None:
        display = str(getattr(city, 'phone', '') or '').strip()
    if not display and settings is not None:
        display = str(getattr(settings, 'default_phone', '') or '').strip()
    return display, phone_tel(display)
