import os

from django.db import models
from django.http import Http404

from src.core.exchange_fields import EXCHANGE_SAFE_HELP, EXCHANGE_SAFE_VERBOSE

_ENV_MODE = 'EXCHANGE_ONLY_MODE'
_ENV_STATUS = 'HIDDEN_PAGE_STATUS'
_REQUEST_MODE = '_exchange_only'
_REQUEST_STATUS = '_hidden_page_status'


def _env_flag(name, allowed):
    raw = os.environ.get(name)
    if raw is None:
        return None
    raw = raw.strip()
    if raw in allowed:
        return raw
    return None


def is_mode_forced_by_env():
    return _env_flag(_ENV_MODE, ('0', '1')) is not None


def is_exchange_only(request=None):
    if request is not None:
        cached = getattr(request, _REQUEST_MODE, None)
        if cached is not None:
            return cached
    forced = _env_flag(_ENV_MODE, ('0', '1'))
    if forced is not None:
        value = forced == '1'
    else:
        from src.core.models import SiteSettings

        stored = SiteSettings.objects.filter(pk=1).values_list(
            'exchange_only', flat=True,
        ).first()
        value = bool(stored)
    if request is not None:
        setattr(request, _REQUEST_MODE, value)
    return value


exchange_only = is_exchange_only


def hidden_page_status(request=None):
    if request is not None:
        cached = getattr(request, _REQUEST_STATUS, None)
        if cached is not None:
            return cached
    forced = _env_flag(_ENV_STATUS, ('503', '404'))
    if forced is not None:
        value = int(forced)
    else:
        from src.core.models import SiteSettings

        stored = SiteSettings.objects.filter(pk=1).values_list(
            'hidden_page_status', flat=True,
        ).first()
        value = int(stored) if stored in (503, 404) else 503
    if request is not None:
        setattr(request, _REQUEST_STATUS, value)
    return value


def raise_hidden():
    """Прихована сторінка. На цьому етапі завжди 404; 503 підключить наступний етап."""
    raise Http404


class ExchangeVisibleQuerySet(models.QuerySet):
    def visible(self):
        if exchange_only():
            return self.filter(exchange_safe=True)
        return self


class ExchangeSafeMixin(models.Model):
    exchange_safe = models.BooleanField(
        EXCHANGE_SAFE_VERBOSE,
        default=False,
        help_text=EXCHANGE_SAFE_HELP,
    )

    objects = ExchangeVisibleQuerySet.as_manager()

    class Meta:
        abstract = True
