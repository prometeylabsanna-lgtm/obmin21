"""Builders for staff notification bodies (plain text + Telegram HTML)."""

from __future__ import annotations

import html

from django.conf import settings
from django.urls import reverse


def admin_change_url(obj) -> str:
    opts = obj._meta
    path = reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[obj.pk])
    base = str(getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    return f'{base}{path}'


def _e(value) -> str:
    return html.escape(str(value if value is not None else ''), quote=False)


def _city_name(obj) -> str:
    city = getattr(obj, 'city', None)
    if city is not None:
        return getattr(city, 'name', '') or ''
    return getattr(obj, 'city_name', '') or ''


def build(kind: str, obj) -> tuple[str, str, str]:
    """Return (subject, plain_text, html_text) for the given submission kind."""
    if kind == 'exchange':
        return _build_exchange(obj)
    if kind == 'contact':
        return _build_contact(obj)
    if kind == 'review':
        return _build_review(obj)
    raise ValueError(f'Unknown notification kind: {kind}')


def _build_exchange(obj) -> tuple[str, str, str]:
    pair = getattr(obj, 'pair', None)
    pair_code = getattr(pair, 'code', '') if pair is not None else ''
    branch = getattr(obj, 'branch', None)
    branch_addr = getattr(branch, 'address', '') if branch is not None else ''
    direction = ''
    if hasattr(obj, 'get_direction_display'):
        direction = obj.get_direction_display()
    expires = ''
    if getattr(obj, 'expires_at', None) is not None:
        expires = obj.expires_at.strftime('%d.%m.%Y %H:%M')
    link = admin_change_url(obj)

    subject = f'Заявка Обмін21 #{obj.pk}'
    plain_lines = [
        f'Нова заявка #{obj.pk}',
        f"Ім'я: {obj.name}",
        f'Телефон: {obj.phone}',
        f'Месенджер: {obj.messenger or "—"}',
        f'Пара: {pair_code}',
        f'Напрямок: {direction}',
        f'Віддає: {obj.amount_give}',
        f'Отримує: {obj.amount_receive}',
        f'Курс: {obj.rate_fixed}',
        f'Місто: {_city_name(obj)}',
        f'Відділення: {branch_addr}',
        f'Дійсна до: {expires}',
        f'Адмін: {link}',
    ]
    html_lines = [
        f'<b>Нова заявка #{_e(obj.pk)}</b>',
        f"Ім'я: {_e(obj.name)}",
        f'Телефон: {_e(obj.phone)}',
        f'Месенджер: {_e(obj.messenger or "—")}',
        f'Пара: {_e(pair_code)}',
        f'Напрямок: {_e(direction)}',
        f'Віддає: {_e(obj.amount_give)}',
        f'Отримує: {_e(obj.amount_receive)}',
        f'Курс: {_e(obj.rate_fixed)}',
        f'Місто: {_e(_city_name(obj))}',
        f'Відділення: {_e(branch_addr)}',
        f'Дійсна до: {_e(expires)}',
        f'Адмін: <a href="{html.escape(link, quote=True)}">відкрити</a>',
    ]
    return subject, '\n'.join(plain_lines), '\n'.join(html_lines)


def _build_contact(obj) -> tuple[str, str, str]:
    link = admin_change_url(obj)
    subject = f'Звернення Обмін21 #{obj.pk}'
    plain_lines = [
        f'Звернення #{obj.pk}',
        f"Ім'я: {obj.name}",
        f'Телефон: {obj.phone}',
        f'Місто: {_city_name(obj) or "—"}',
        f'Повідомлення: {obj.message}',
        f'Адмін: {link}',
    ]
    html_lines = [
        f'<b>Звернення #{_e(obj.pk)}</b>',
        f"Ім'я: {_e(obj.name)}",
        f'Телефон: {_e(obj.phone)}',
        f'Місто: {_e(_city_name(obj) or "—")}',
        f'Повідомлення: {_e(obj.message)}',
        f'Адмін: <a href="{html.escape(link, quote=True)}">відкрити</a>',
    ]
    return subject, '\n'.join(plain_lines), '\n'.join(html_lines)


def _build_review(obj) -> tuple[str, str, str]:
    link = admin_change_url(obj)
    city = getattr(obj, 'city_name', '') or '—'
    phone = getattr(obj, 'phone', '') or '—'
    subject = f'Відгук Обмін21 #{obj.pk}'
    plain_lines = [
        f'Новий відгук #{obj.pk}',
        f"Ім'я: {obj.name}",
        f'Місто: {city}',
        f'Оцінка: {obj.rating}',
        f'Текст: {obj.text}',
        f'Телефон: {phone}',
        f'Адмін: {link}',
    ]
    html_lines = [
        f'<b>Новий відгук #{_e(obj.pk)}</b>',
        f"Ім'я: {_e(obj.name)}",
        f'Місто: {_e(city)}',
        f'Оцінка: {_e(obj.rating)}',
        f'Текст: {_e(obj.text)}',
        f'Телефон: {_e(phone)}',
        f'Адмін: <a href="{html.escape(link, quote=True)}">відкрити</a>',
    ]
    return subject, '\n'.join(plain_lines), '\n'.join(html_lines)
