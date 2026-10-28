"""Розбір тексту графіка відділення і JSON-LD OpeningHoursSpecification."""

import re
from datetime import time

WEEKDAYS = (
    (0, 'Пн'),
    (1, 'Вт'),
    (2, 'Ср'),
    (3, 'Чт'),
    (4, 'Пт'),
    (5, 'Сб'),
    (6, 'Нд'),
)

SCHEMA_DAYS = (
    'https://schema.org/Monday',
    'https://schema.org/Tuesday',
    'https://schema.org/Wednesday',
    'https://schema.org/Thursday',
    'https://schema.org/Friday',
    'https://schema.org/Saturday',
    'https://schema.org/Sunday',
)

_DAY_INDEX = {label.casefold(): index for index, label in WEEKDAYS}
_DASH = '[-\u2013]'
_DAY = r'пн|вт|ср|чт|пт|сб|нд'
_CLOCK = r'(?:[01]?\d|2[0-3]):[0-5]\d'
_GROUP = re.compile(
    rf'(?P<start>{_DAY})(?:\s*{_DASH}\s*(?P<end>{_DAY}))?'
    rf'\s*,?\s*'
    rf'(?P<opens>{_CLOCK})\s*{_DASH}\s*(?P<closes>{_CLOCK})',
    re.IGNORECASE,
)


def _clock(value):
    hour_text, minute_text = value.split(':')
    hour = int(hour_text)
    minute = int(minute_text)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def parse_hours(text):
    """Список (день 0=Пн..6=Нд, opens, closes) або None, якщо текст не розібрати.

    Дні, яких немає в тексті, вихідні: у список вони не входять.
    """
    if not isinstance(text, str):
        return None
    raw = ' '.join(text.split())
    if not raw:
        return None
    slots = []
    seen = set()
    pos = 0
    found = False
    for match in _GROUP.finditer(raw):
        gap = raw[pos:match.start()]
        if not found:
            if gap.strip():
                return None
        elif ',' not in gap or gap.strip(' ,'):
            return None
        found = True
        start = _DAY_INDEX[match.group('start').casefold()]
        end_raw = match.group('end')
        end = start if end_raw is None else _DAY_INDEX[end_raw.casefold()]
        if end < start:
            return None
        opens = _clock(match.group('opens'))
        closes = _clock(match.group('closes'))
        if opens is None or closes is None or opens >= closes:
            return None
        for day in range(start, end + 1):
            if day in seen:
                return None
            seen.add(day)
            slots.append((day, opens, closes))
        pos = match.end()
    if not found or raw[pos:].strip(' ,'):
        return None
    return slots


def _hhmm(value):
    return value.strftime('%H:%M')


def opening_hours_specification(slots):
    """Групи днів з однаковим часом. Вихідні не потрапляють у список."""
    if not slots:
        return []
    groups = {}
    used = set()
    ordered = sorted(slots, key=lambda item: item[0])
    for day, opens, closes in ordered:
        if day in used or not isinstance(day, int) or day < 0 or day > 6:
            continue
        if opens is None or closes is None:
            continue
        used.add(day)
        key = (_hhmm(opens), _hhmm(closes))
        groups.setdefault(key, []).append(day)
    spec = []
    for (opens, closes), days in groups.items():
        spec.append({
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': [SCHEMA_DAYS[day] for day in days],
            'opens': opens,
            'closes': closes,
        })
    return spec


def _structured_rows(branch):
    related = getattr(branch, 'opening_hours', None)
    if not hasattr(related, 'all'):
        return None
    rows = list(related.all())
    if not rows:
        return None
    return rows


def open_slots(branch):
    """Рядки графіка, якщо вони є. Інакше розбір Branch.hours. None — не розібрати."""
    rows = _structured_rows(branch)
    if rows is not None:
        slots = []
        for row in rows:
            if getattr(row, 'is_closed', False):
                continue
            opens = getattr(row, 'opens', None)
            closes = getattr(row, 'closes', None)
            if opens is None or closes is None:
                continue
            try:
                day = int(row.day_of_week)
            except (TypeError, ValueError):
                continue
            slots.append((day, opens, closes))
        return slots
    text = getattr(branch, 'hours', '') or ''
    return parse_hours(text)
