from django import template

from src.core.exchange_mode import (
    NEUTRAL_DESCRIPTION,
    is_exchange_only as exchange_only_enabled,
    mode_meta as mode_meta_value,
    mode_text,
)

register = template.Library()


def _site_name(context):
    settings = context.get('site_settings')
    if settings is not None and hasattr(settings, 'site_name'):
        return settings.site_name
    from src.core.models import SiteSettings

    return SiteSettings.load().site_name


@register.simple_tag(takes_context=True)
def is_exchange_only(context):
    return exchange_only_enabled(context.get('request'))


@register.simple_tag(takes_context=True)
def mode_field(context, obj, field):
    return mode_text(obj, field, request=context.get('request'))


@register.simple_tag(takes_context=True)
def mode_meta(context, obj, *fields):
    request = context.get('request')
    text = mode_meta_value(obj, *fields, limit=None, request=request)
    if exchange_only_enabled(request) and text == NEUTRAL_DESCRIPTION:
        return _site_name(context)
    return text
