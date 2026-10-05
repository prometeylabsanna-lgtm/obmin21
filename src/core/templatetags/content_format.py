import re
from decimal import Decimal, InvalidOperation

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


@register.filter(name='format_rate')
def format_rate(value, style='fixed4'):
    """
    Format exchange rate for display.
    - fixed4: always 4 decimals (41.2000) — retail/wholesale/cross
    - compact: strip trailing zeros (2410000, 41.2) — crypto / money amounts
    - auto: compact if |value| >= 1000, else fixed4
    """
    if value is None or value == '':
        return ''
    try:
        amount = Decimal(str(value).replace(',', '.').replace(' ', ''))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    mode = (style or 'fixed4').strip().lower()
    if mode == 'auto':
        mode = 'compact' if abs(amount) >= Decimal('1000') else 'fixed4'

    if mode == 'compact':
        text = format(amount.normalize(), 'f')
        if '.' in text:
            text = text.rstrip('0').rstrip('.')
        return text

    quantized = amount.quantize(Decimal('0.0001'))
    return format(quantized, 'f')


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


def _paragraph(inner: str) -> str:
    return f'<p>{inner}</p>'


@register.filter(name='format_legal')
def format_legal(value):
    """Legal text: intro + section cards from short standalone headings."""
    if not value:
        return ''
    blocks = re.split(r'\n\s*\n', str(value).strip())
    intro = []
    sections = []
    current = None

    def close_section():
        nonlocal current
        if not current:
            return
        paras = ''.join(_paragraph(item) for item in current['paras'])
        sections.append(
            '<section class="legal-block">'
            f'<h2 class="legal-block__title">{current["title"]}</h2>'
            f'<div class="legal-block__text">{paras}</div>'
            '</section>'
        )
        current = None

    for block in blocks:
        lines = [ln.strip() for ln in block.split('\n') if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and _is_heading(lines[0]):
            close_section()
            current = {'title': mark_brand(lines[0]), 'paras': []}
            continue
        inner = '<br>'.join(mark_brand(ln) for ln in lines)
        if current is None:
            intro.append(inner)
        else:
            current['paras'].append(inner)
    close_section()

    parts = []
    if intro:
        parts.append(
            '<div class="legal-page__intro">'
            + ''.join(_paragraph(item) for item in intro)
            + '</div>'
        )
    if sections:
        parts.append(
            '<div class="legal-stack">' + ''.join(sections) + '</div>'
        )
    return mark_safe(''.join(parts))
