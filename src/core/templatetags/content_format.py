import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_HEADING_END = ('.', '!', '?', ':', '…', ';', ',')
_BRAND_RE = re.compile(r'(обмін)(21)', re.IGNORECASE)


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


def mark_brand(text: str) -> str:
    """Escape plain text and wrap Обмін21 with brand markup."""
    if not text:
        return ''
    parts = []
    last = 0
    for match in _BRAND_RE.finditer(text):
        parts.append(escape(text[last:match.start()]))
        word = escape(match.group(1))
        digits = escape(match.group(2))
        parts.append(
            f'<span class="brand-mark">{word}'
            f'<span class="u-accent">{digits}</span></span>'
        )
        last = match.end()
    parts.append(escape(text[last:]))
    return ''.join(parts)


@register.filter(name='brand_mark')
def brand_mark(value):
    """Highlight Обмін21 in plain text (newlines → <br>)."""
    if not value:
        return ''
    lines = str(value).split('\n')
    return mark_safe('<br>'.join(mark_brand(line) for line in lines))


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
                f'<h3 class="detail-page__subhead">{mark_brand(lines[0])}</h3>'
            )
            continue
        inner = '<br>'.join(mark_brand(ln) for ln in lines)
        parts.append(f'<p>{inner}</p>')
    return mark_safe(''.join(parts))
