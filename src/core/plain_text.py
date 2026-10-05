from html import unescape

from django.utils.html import strip_tags


def plain_text(value: str) -> str:
    return unescape(strip_tags(value or '')).replace('\xa0', ' ').strip()
