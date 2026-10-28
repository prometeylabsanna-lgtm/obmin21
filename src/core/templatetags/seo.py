from django import template

from src.core.seo import build_head

register = template.Library()


@register.inclusion_tag('core/seo_head.html', takes_context=True)
def seo_head(context):
    return build_head(context.get('request'), context)
