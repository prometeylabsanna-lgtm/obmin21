import os

from django.db import models
from django.db.models import Q
from django.http import Http404

from src.core.exchange_classify import (
    CONTENT_CURRENCY,
    PAIR_FIAT,
    VISIBILITY_AUTO,
    VISIBILITY_HIDE,
    VISIBILITY_SHOW,
)
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


def mode_text(obj, field, request=None):
    """Поза режимом — поле як є. У режимі — лише strip ``field_mode``, інакше ''."""
    if not is_exchange_only(request):
        return getattr(obj, field)
    value = getattr(obj, field + '_mode', '')
    if value is None:
        return ''
    return str(value).strip()


NEUTRAL_DESCRIPTION = 'Обмін готівкової валюти у касі'


def mode_meta(obj, *fields, limit=160, request=None, outside_default=''):
    """Перше непорожнє поле для title або description.

    Поза режимом значення як у ``a or b``: поля після першого ріжуться до
    ``limit``, якщо ліміт задано. Порожній ланцюжок повертає ``outside_default``.

    У режимі лише ``mode_text``. Якщо всі ``*_mode`` порожні або поля немає,
    повертає ``NEUTRAL_DESCRIPTION``.
    """
    in_mode = is_exchange_only(request)
    for index, field in enumerate(fields):
        if in_mode:
            text = mode_text(obj, field, request)
        else:
            raw = getattr(obj, field, '')
            if raw is None:
                text = ''
            elif isinstance(raw, str):
                text = raw
            else:
                text = str(raw)
        if text and index and limit is not None:
            text = text[:limit]
        if text:
            return text
    if in_mode:
        return NEUTRAL_DESCRIPTION
    return outside_default


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


class ExchangeVisibility(models.TextChoices):
    AUTO = VISIBILITY_AUTO, 'Авто'
    SHOW = VISIBILITY_SHOW, 'Показувати'
    HIDE = VISIBILITY_HIDE, 'Приховати'


def exchange_mode_public_q(model):
    """Запис видимий у режимі «Лише обмін», незалежно від того, чи режим увімкнений."""
    names = {field.name for field in model._meta.concrete_fields}
    if 'exchange_visibility' not in names:
        if 'exchange_safe' in names:
            return Q(exchange_safe=True)
        return Q()
    hidden = Q(exchange_visibility=ExchangeVisibility.HIDE)
    shown = Q(exchange_visibility=ExchangeVisibility.SHOW)
    legacy = Q(
        exchange_visibility=ExchangeVisibility.AUTO,
        exchange_safe=True,
    )
    auto = Q(
        exchange_visibility=ExchangeVisibility.AUTO,
        exchange_safe=False,
    )
    if 'kind' in names:
        auto &= Q(kind=PAIR_FIAT)
    elif 'content_kind' in names:
        auto &= Q(content_kind=CONTENT_CURRENCY)
    else:
        auto = Q(pk__in=[])
    return ~hidden & (shown | legacy | auto)


def hidden_in_exchange_mode(queryset):
    return queryset.exclude(exchange_mode_public_q(queryset.model))


def shows_in_exchange_mode(obj, request=None):
    """Чи показувати запис у шаблоні. Поза режимом — так."""
    if obj is None:
        return False
    if not is_exchange_only(request):
        return True
    visibility = getattr(obj, 'exchange_visibility', VISIBILITY_AUTO)
    if visibility == VISIBILITY_HIDE:
        return False
    if visibility == VISIBILITY_SHOW or getattr(obj, 'exchange_safe', False):
        return True
    if getattr(obj, 'kind', '') == PAIR_FIAT:
        return True
    return getattr(obj, 'content_kind', '') == CONTENT_CURRENCY


class ExchangeVisibleQuerySet(models.QuerySet):
    def visible(self):
        if exchange_only():
            return self.filter(exchange_mode_public_q(self.model))
        return self


class ExchangeSafeMixin(models.Model):
    exchange_safe = models.BooleanField(
        EXCHANGE_SAFE_VERBOSE,
        default=False,
        help_text=EXCHANGE_SAFE_HELP,
    )
    exchange_visibility = models.CharField(
        'Видимість у режимі «Лише обмін»',
        max_length=8,
        choices=ExchangeVisibility.choices,
        default=ExchangeVisibility.AUTO,
        help_text=(
            'Авто — за типом: фіат і валютні матеріали видимі, '
            'крипто, метал, SWIFT і перекази приховані. '
            'Показувати і Приховати сильніші за тип і за стару галочку.'
        ),
    )

    objects = ExchangeVisibleQuerySet.as_manager()

    class Meta:
        abstract = True

    def apply_exchange_classification(self):
        return ()

    def save(self, *args, **kwargs):
        changed = []
        if self.exchange_visibility not in {
            ExchangeVisibility.AUTO,
            ExchangeVisibility.SHOW,
            ExchangeVisibility.HIDE,
        }:
            self.exchange_visibility = ExchangeVisibility.AUTO
            changed.append('exchange_visibility')
        changed.extend(self.apply_exchange_classification() or ())
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and changed:
            kwargs['update_fields'] = list(dict.fromkeys([*update_fields, *changed]))
        super().save(*args, **kwargs)
