"""Геокодування адреси відділення через Nominatim і правило координат в адмінці.

Правило збереження відділення (форма відділення і інлайн у місті):
1. Якщо у формі змінилися широта або довгота і хоча б одне поле заповнене:
   coords_manual=True, геокодування не викликається.
2. Якщо обидві координати очищені вручну: coords_manual=False.
   Геокодування в цьому збереженні не викликається. Наступна зміна адреси
   знову визначить координати сама.
3. Інакше, якщо змінилася адреса і coords_manual є хибним: широта і довгота
   скидаються в None, далі пошук. Успіх — messages.info. Нічого не знайдено —
   messages.warning: координати не знайдено, карта лишається за адресою,
   широту й довготу можна ввести вручну.
4. Без справжньої адреси пошук не виконується і повертає None.

Пошук: https://nominatim.openstreetmap.org/search
Параметри: format=jsonv2, limit=1, countrycodes=ua, timeout 5 с.
User-Agent: Obmin21/1.0 (+домен із settings.SITE_URL, якщо він є).
Запит — адреса з нормалізованими пробілами. Якщо назви міста в ній немає,
дописується назва міста.
Результат приймається лише для будинку: addresstype або type зі списку
будівель і закладів, або в address є house_number. Інакше None.
Будь-яка помилка дає None, виняток назовні не йде.
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages

from src.network.models import normalize_address

NOMINATIM_SEARCH = 'https://nominatim.openstreetmap.org/search'
_TIMEOUT = 5
_READ_LIMIT = 1_048_576
_SCALE = Decimal('0.000001')

GEOCODE_SUCCESS = 'Координати визначено. Карта використає знайдену точку.'
GEOCODE_FAILURE = (
    'Координати не знайдено. Карта використовує адресу. '
    'Широту й довготу можна ввести вручну.'
)

HOUSE_LEVEL_TYPES = frozenset({
    'building',
    'house',
    'shop',
    'amenity',
    'apartments',
    'apartment',
    'commercial',
    'office',
    'retail',
    'hotel',
    'hostel',
    'yes',
    'detached',
    'terrace',
    'semidetached_house',
    'farm',
    'industrial',
    'warehouse',
    'kiosk',
    'public_building',
    'bungalow',
    'cabin',
    'houseboat',
    'static_caravan',
    'civic',
    'government',
    'bank',
    'clinic',
    'hospital',
    'pharmacy',
    'school',
    'university',
    'kindergarten',
    'place_of_worship',
    'restaurant',
    'cafe',
    'fast_food',
    'house_number',
    'address',
})


def nominatim_user_agent():
    raw = str(getattr(settings, 'SITE_URL', '') or '').strip()
    host = urlparse(raw).hostname or '' if raw else ''
    if host:
        return f'Obmin21/1.0 (+{host})'
    return 'Obmin21/1.0'


def geocode_action_summary(found, missing, manual, unreal):
    return (
        f'Визначено координати: {found}. '
        f'Не знайдено: {missing}. '
        f'Пропущено, бо координати введено вручну: {manual}. '
        f'Пропущено, бо немає справжньої адреси: {unreal}.'
    )


def _coord(value, limit):
    if value is None or isinstance(value, bool):
        return None
    number = Decimal(str(value).strip())
    if not number.is_finite():
        return None
    number = number.quantize(_SCALE, rounding=ROUND_HALF_UP)
    if number < -limit or number > limit:
        return None
    return number


def _is_house_level(item):
    if not isinstance(item, dict):
        return False
    address = item.get('address')
    if isinstance(address, dict):
        number = address.get('house_number')
        if number is not None and str(number).strip():
            return True
    for key in ('addresstype', 'type'):
        token = str(item.get(key) or '').strip().casefold()
        if token in HOUSE_LEVEL_TYPES:
            return True
    return False


def _pair(item):
    if not isinstance(item, dict):
        return None
    lat = _coord(item.get('lat'), Decimal('90'))
    lng = _coord(item.get('lon'), Decimal('180'))
    if lat is None or lng is None:
        return None
    return lat, lng


def _search_query(branch):
    address = normalize_address(getattr(branch, 'address', ''))
    city_name = normalize_address(getattr(getattr(branch, 'city', None), 'name', ''))
    if city_name and city_name.casefold() not in address.casefold():
        return f'{address}, {city_name}'
    return address


def _fetch(url, user_agent):
    request = Request(
        url,
        headers={
            'User-Agent': user_agent,
            'Accept': 'application/json',
        },
    )
    with urlopen(request, timeout=_TIMEOUT) as response:
        raw = response.read(_READ_LIMIT + 1)
    if len(raw) > _READ_LIMIT:
        return None
    return json.loads(raw.decode('utf-8'))


def geocode_branch(branch):
    """(широта, довгота) будинку або None. Не кидає винятків."""
    try:
        if branch is None or not getattr(branch, 'has_real_address', False):
            return None
        query = _search_query(branch)
        if not query:
            return None
        params = urlencode({
            'q': query,
            'format': 'jsonv2',
            'limit': 1,
            'countrycodes': 'ua',
        })
        payload = _fetch(f'{NOMINATIM_SEARCH}?{params}', nominatim_user_agent())
        if not isinstance(payload, list) or not payload:
            return None
        hit = payload[0]
        if not _is_house_level(hit):
            return None
        return _pair(hit)
    except Exception:
        return None


def geocode_saved_branch(branch):
    point = geocode_branch(branch)
    if point is None:
        return False
    branch.lat, branch.lng = point
    if getattr(branch, 'pk', None):
        branch.save(update_fields=['lat', 'lng'])
    return True


def geocode_queryset(branches):
    found = missing = manual = unreal = 0
    for branch in branches:
        if getattr(branch, 'coords_manual', False):
            manual += 1
            continue
        if not getattr(branch, 'has_real_address', False):
            unreal += 1
            continue
        if geocode_saved_branch(branch):
            found += 1
        else:
            missing += 1
    return {
        'found': found,
        'missing': missing,
        'manual': manual,
        'unreal': unreal,
    }


def _notify(request, level, text):
    if request is None:
        return
    level(request, text)


def apply_admin_coordinates(request, branch, form):
    """Застосовує правило координат із докстрінга модуля до вже очищеної форми."""
    changed = set(getattr(form, 'changed_data', ()) or ())
    if 'lat' in changed or 'lng' in changed:
        if branch.lat is None and branch.lng is None:
            branch.coords_manual = False
        else:
            branch.coords_manual = True
        return
    address_changed = 'address' in changed
    if (
        getattr(branch, 'pk', None) is None
        and normalize_address(getattr(branch, 'address', ''))
    ):
        address_changed = True
    if not address_changed or branch.coords_manual:
        return
    branch.lat = None
    branch.lng = None
    point = geocode_branch(branch)
    if point is None:
        if branch.has_real_address:
            _notify(request, messages.warning, GEOCODE_FAILURE)
        return
    branch.lat, branch.lng = point
    _notify(request, messages.info, GEOCODE_SUCCESS)
