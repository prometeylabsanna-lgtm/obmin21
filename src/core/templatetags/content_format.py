import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_HEADING_END = ('.', '!', '?', ':', '…', ';', ',')


def _is_heading(line: str) -> bool:
    text = line.strip()
    if not text or len(text) > 72:
        return False
    if text[0].isdigit():
        return False
    if text.endswith(_HEADING_END):
        return False
    if text.count(' ') > 8:
        return False
    return True


@register.filter(name='format_body')
def format_body(value):
    """Split plain text into paragraphs; short standalone lines become subheads."""
    if not value:
        return ''
    blocks = re.split(r'\n\s*\n', str(value).strip())
    parts = []
    for block in blocks:
        lines = [ln.strip() for ln in block.split('\n') if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and _is_heading(lines[0]):
            parts.append(
                f'<h3 class="detail-page__subhead">{escape(lines[0])}</h3>'
            )
            continue
        inner = '<br>'.join(escape(ln) for ln in lines)
        parts.append(f'<p>{inner}</p>')
    return mark_safe(''.join(parts))
