import json
import re
from html import escape, unescape
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from src.core.exchange_mode import is_exchange_only
from src.core.hidden_response import is_hidden_path
from src.core.seo_words import contains_stop_word, strip_stop_words

_SKIP_PREFIXES = ('/admin', '/tinymce', '/static', '/media')
_TITLE_FALLBACK = 'Обмін валют'
_DROP = object()
_META_RE = re.compile(r'<meta\b[^>]*>', re.I)
_LINK_RE = re.compile(r'<link\b[^>]*>', re.I)
_TITLE_RE = re.compile(r'(<title\b[^>]*>)(.*?)(</title>)', re.I | re.S)
_JSONLD_RE = re.compile(
    r'<script\b[^>]*\btype\s*=\s*(["\'])application/ld\+json\1[^>]*>.*?</script>',
    re.I | re.S,
)
_SCRIPT_PARTS_RE = re.compile(r'^(<script\b[^>]*>)(.*)(</script>)$', re.I | re.S)
_TEXT_OG = {'og:title', 'og:description', 'og:site_name', 'og:image:alt'}


def clean_public_url(url, request=None):
    raw = unescape((url or '').strip())
    if not raw:
        return ''
    parts = urlsplit(raw)
    path = parts.path or ''
    if path and is_hidden_path(path, request):
        return ''
    if path and contains_stop_word(unquote(path)):
        return ''
    query = parts.query
    fragment = parts.fragment
    query_changed = False
    if query:
        kept = []
        for key, value in parse_qsl(query, keep_blank_values=True):
            if contains_stop_word(unquote(key)) or contains_stop_word(unquote(value)):
                query_changed = True
                continue
            kept.append((key, value))
        if query_changed:
            query = urlencode(kept)
    fragment_changed = bool(fragment) and contains_stop_word(unquote(fragment))
    if fragment_changed:
        fragment = ''
    if not query_changed and not fragment_changed:
        return raw
    return urlunsplit((parts.scheme, parts.netloc, path, query, fragment))


def sanitize_public_html(html, request=None):
    if not html:
        return html
    html = _TITLE_RE.sub(lambda match: _rewrite_title(match), html, count=1)
    html = _rewrite_tags(html, _META_RE, lambda tag: _rewrite_meta(tag, request))
    html = _rewrite_tags(html, _LINK_RE, lambda tag: _rewrite_link(tag, request))
    html = _rewrite_tags(html, _JSONLD_RE, lambda tag: _rewrite_jsonld(tag, request))
    return html


def sanitize_response(request, response):
    if not is_exchange_only(request) or response.status_code != 200:
        return response
    if getattr(response, 'streaming', False):
        return response
    content_type = response.get('Content-Type', '')
    if 'html' not in content_type.lower():
        return response
    path = getattr(request, 'path_info', '') or ''
    if path.startswith(_SKIP_PREFIXES):
        return response
    charset = getattr(response, 'charset', None) or 'utf-8'
    try:
        html = response.content.decode(charset)
    except (AttributeError, UnicodeDecodeError):
        return response
    cleaned = sanitize_public_html(html, request)
    if cleaned != html:
        response.content = cleaned.encode(charset)
    return response


class PublicSeoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return sanitize_response(request, self.get_response(request))


def _rewrite_tags(html, pattern, rewriter):
    pieces = []
    last = 0
    for match in pattern.finditer(html):
        pieces.append(html[last:match.start()])
        updated = rewriter(match.group(0))
        pieces.append(match.group(0) if updated is None else updated)
        last = match.end()
    pieces.append(html[last:])
    return ''.join(pieces)


def _rewrite_title(match):
    inner = unescape(match.group(2))
    if not contains_stop_word(inner):
        return match.group(0)
    cleaned = strip_stop_words(inner) or _TITLE_FALLBACK
    return f'{match.group(1)}{escape(cleaned)}{match.group(3)}'


def _rewrite_meta(tag, request):
    kind = _meta_kind(tag)
    if kind is None:
        return None
    return _rewrite_content(tag, request, kind)


def _rewrite_link(tag, request):
    rel = (_attr(tag, 'rel') or '').lower()
    if rel == 'canonical' or (rel == 'alternate' and _attr(tag, 'hreflang')):
        return _rewrite_named_attr(tag, 'href', request, 'url')
    return None


def _rewrite_content(tag, request, kind):
    return _rewrite_named_attr(tag, 'content', request, kind)


def _rewrite_named_attr(tag, name, request, kind):
    current = _attr(tag, name)
    if current is None:
        return None
    if kind == 'url':
        cleaned = clean_public_url(current, request)
        if not cleaned:
            return ''
    else:
        if not contains_stop_word(current):
            return None
        cleaned = strip_stop_words(current)
        if not cleaned:
            return ''
    if cleaned == current:
        return None
    return _set_attr(tag, name, cleaned)


def _rewrite_jsonld(tag, request):
    parts = _SCRIPT_PARTS_RE.match(tag)
    if not parts:
        return None
    raw = parts.group(2).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    cleaned = _sanitize_json(data, request)
    if cleaned is _DROP or cleaned in ({}, []):
        return ''
    if cleaned == data:
        return None
    payload = json.dumps(cleaned, ensure_ascii=False, separators=(',', ':'))
    payload = (
        payload.replace('<', '\\u003c')
        .replace('>', '\\u003e')
        .replace('&', '\\u0026')
    )
    return f'{parts.group(1)}{payload}{parts.group(3)}'


def _sanitize_json(value, request):
    if isinstance(value, str):
        return _sanitize_json_string(value, request)
    if isinstance(value, list):
        changed = False
        items = []
        for item in value:
            new_item = _sanitize_json(item, request)
            if new_item is _DROP or new_item in ({}, []):
                changed = True
                continue
            if new_item != item:
                changed = True
            items.append(new_item)
        if changed and not items:
            return _DROP
        return items if changed else value
    if isinstance(value, dict):
        changed = False
        cleaned = {}
        for key, item in value.items():
            new_item = _sanitize_json(item, request)
            if new_item is _DROP or new_item in ({}, []):
                changed = True
                continue
            if new_item != item:
                changed = True
            cleaned[key] = new_item
        if changed and not cleaned:
            return _DROP
        return cleaned if changed else value
    return value


def _sanitize_json_string(value, request):
    if _looks_like_url(value):
        cleaned = clean_public_url(value, request)
        if not cleaned:
            return _DROP
        return value if cleaned == unescape(value).strip() else cleaned
    if not contains_stop_word(value):
        return value
    stripped = strip_stop_words(value)
    if not stripped:
        return _DROP
    return stripped


def _meta_kind(tag):
    key = ((_attr(tag, 'property') or _attr(tag, 'name') or '')).lower()
    if key == 'description':
        return 'text'
    if key.startswith('og:'):
        return 'text' if key in _TEXT_OG else 'url'
    return None


def _looks_like_url(value):
    text = value.strip()
    return text.startswith(('http://', 'https://', '/'))


def _attr(tag, name):
    match = re.search(
        rf'\b{name}\s*=\s*(["\'])(.*?)\1',
        tag,
        re.I | re.S,
    )
    if not match:
        return None
    return unescape(match.group(2))


def _set_attr(tag, name, value):
    escaped = escape(value, quote=True)
    pattern = re.compile(
        rf'(\b{name}\s*=\s*)(["\'])(.*?)(\2)',
        re.I | re.S,
    )

    def replacer(match):
        return f'{match.group(1)}{match.group(2)}{escaped}{match.group(4)}'

    return pattern.sub(replacer, tag, count=1)
