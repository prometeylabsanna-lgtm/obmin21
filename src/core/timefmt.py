"""Форматування дат для повідомлень клієнту/менеджеру завжди в TIME_ZONE (Europe/Kyiv)."""

from __future__ import annotations

from django.utils import timezone


def local_dt(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        return value
    return timezone.localtime(value)


def local_fmt(value, fmt: str = '%H:%M %d.%m.%Y') -> str:
    value = local_dt(value)
    return value.strftime(fmt) if value is not None else ''
