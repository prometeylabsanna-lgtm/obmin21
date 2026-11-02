"""Санітизація HTML з TinyMCE / rich_html (nh3)."""

from __future__ import annotations

import nh3

ALLOWED_TAGS = frozenset({
    'p',
    'br',
    'strong',
    'b',
    'em',
    'i',
    'u',
    's',
    'ul',
    'ol',
    'li',
    'a',
    'h2',
    'h3',
    'h4',
    'blockquote',
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
    'img',
    'span',
})

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt', 'width', 'height'},
}

ALLOWED_URL_SCHEMES = frozenset({'http', 'https', 'mailto', 'tel'})


def sanitize_rich_html(value: str | None) -> str:
    """Allowlist-теги; без script/iframe/style/on*; лише безпечні URL."""
    text = str(value or '')
    if not text.strip():
        return ''
    return nh3.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel='noopener noreferrer',
    )
