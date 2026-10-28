from django import template
from django.utils.html import format_html

from src.core.responsive_images import field_size, static_image, static_size

register = template.Library()


@register.simple_tag
def static_img(name):
    return static_image(name)


@register.simple_tag
def img_wh(name):
    width, height = static_size(name)
    if not width or not height:
        return ''
    return format_html('width="{}" height="{}"', width, height)


@register.simple_tag
def field_wh(field):
    width, height = field_size(field)
    if not width or not height:
        return ''
    return format_html('width="{}" height="{}"', width, height)
