"""Обмеження частоти POST за IP (django cache)."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache

DEFAULT_LIMIT = 3
DEFAULT_WINDOW = 600  # 10 хвилин


def client_ip(request) -> str:
    """IP, який дописав єдиний nginx ($proxy_add_x_forwarded_for — у кінець списку)."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR') or ''
    parts = [part.strip() for part in forwarded.split(',') if part.strip()]
    if parts:
        return parts[-1]
    return (request.META.get('REMOTE_ADDR') or '').strip() or 'unknown'


def allow_request(request, action: str, *, limit=DEFAULT_LIMIT, window=DEFAULT_WINDOW) -> bool:
    """True, якщо запит ще в ліміті; лічильник збільшується на кожен виклик."""
    if not getattr(settings, 'RATELIMIT_ENABLE', True):
        return True
    key = f'rl:{action}:{client_ip(request)}'
    count = cache.get(key, 0)
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0
    if count >= limit:
        return False
    cache.set(key, count + 1, window)
    return True
