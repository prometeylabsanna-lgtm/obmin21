from django import template

from src.core.exchange_mode import (
    is_exchange_only as exchange_only_enabled,
    mode_text,
)

register = template.Library()


@register.simple_tag(takes_context=True)
def is_exchange_only(context):
    return exchange_only_enabled(context.get('request'))


@register.simple_tag(takes_context=True)
def mode_field(context, obj, field):
    return mode_text(obj, field, request=context.get('request'))
