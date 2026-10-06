from django import template
from django.utils.safestring import mark_safe

from src.bot.html import sanitize_bot_html

register = template.Library()


@register.filter(name='bot_html')
def bot_html(value):
    return mark_safe(sanitize_bot_html(value))
