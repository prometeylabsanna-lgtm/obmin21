from django import template

from src.core.exchange_mode import is_exchange_only as exchange_only_enabled

register = template.Library()


@register.simple_tag(takes_context=True)
def is_exchange_only(context):
    return exchange_only_enabled(context.get('request'))
