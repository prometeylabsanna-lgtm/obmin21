"""Обхід публічних сторінок у режимі «лише обмін»: стоп-слова не мають світитися."""

import os
import re
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.utils import translation

from src.core.tests.eo_realdb import (
    RealDataTestCase,
    classify_eur_usd,
    copy_real_db,
    discover_public_paths,
    language_prefixes,
    prefix_path,
    restore_test_db,
    spider_extra_paths,
)

SPIDER_URLS_FILE = Path('/tmp/obmin21_spider_urls.txt')
_TEXT_TYPES = frozenset({
    'text/plain',
    'text/css',
    'application/json',
    'application/xml',
    'text/xml',
    'application/javascript',
    'text/javascript',
})


def setUpModule():
    copy_real_db()


def tearDownModule():
    restore_test_db()


class _VisibleParts(HTMLParser):
    """Видимий текст, title, meta, og, JSON-LD, alt і option. script/style пропускає."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.capture = None
        self.buf = []
        self.visible = []
        self.title = ''
        self.json_ld = []
        self.alts = []
        self.metas = []
        self.options = []

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, closed=False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, closed=True)

    def _open(self, tag, attrs, closed):
        tag = tag.lower()
        attr = {key.lower(): value or '' for key, value in attrs}
        if self.skip_depth or self.capture == 'jsonld':
            if tag in ('script', 'style') and not closed:
                self.skip_depth += 1
            return
        if tag == 'script':
            if 'ld+json' in attr.get('type', '').lower().replace(' ', '') and not closed:
                self.capture = 'jsonld'
                self.buf = []
            elif not closed:
                self.skip_depth = 1
            return
        if tag == 'style':
            if not closed:
                self.skip_depth = 1
            return
        if tag == 'title' and not closed:
            self.capture = 'title'
            self.buf = []
            return
        if tag == 'option' and not closed:
            self.capture = 'option'
            self.buf = []
            return
        if attr.get('alt'):
            self.alts.append(attr['alt'])
        if tag == 'meta':
            self._meta(attr)

    def _meta(self, attr):
        content = attr.get('content', '')
        if not content:
            return
        name = attr.get('name', '').strip().lower()
        prop = attr.get('property', '').strip().lower()
        if name in ('description', 'keywords'):
            self.metas.append((f'meta {name}', content))
        key = prop if prop.startswith('og:') else name if name.startswith('og:') else ''
        if key:
            self.metas.append((key, content))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'script' and self.capture == 'jsonld':
            self.json_ld.append(''.join(self.buf))
            self.capture = None
            self.buf = []
            return
        if tag in ('script', 'style') and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth or self.capture == 'jsonld':
            return
        if tag == 'title' and self.capture == 'title':
            self.title = ''.join(self.buf)
            self.capture = None
            self.buf = []
            return
        if tag == 'option' and self.capture == 'option':
            self.options.append(''.join(self.buf))
            self.capture = None
            self.buf = []

    def handle_data(self, data):
        if self.skip_depth or not data:
            return
        if self.capture in ('title', 'option', 'jsonld'):
            self.buf.append(data)
            return
        self.visible.append(data)

    def close(self):
        super().close()
        if self.capture == 'title':
            self.title = ''.join(self.buf)
        elif self.capture == 'option':
            self.options.append(''.join(self.buf))
        elif self.capture == 'jsonld':
            self.json_ld.append(''.join(self.buf))

    def chunks(self):
        parts = [('text', ' '.join(self.visible)), ('title', self.title)]
        parts.extend(self.metas)
        parts.extend(('json-ld', block) for block in self.json_ld)
        parts.extend(('alt', alt) for alt in self.alts)
        parts.extend(('option', option) for option in self.options)
        return parts


def _scan_kind(content_type):
    kind = (content_type or '').split(';', 1)[0].strip().lower()
    if kind in ('text/html', 'application/xhtml+xml'):
        return 'html'
    if kind in _TEXT_TYPES:
        return 'text'
    return ''


def compile_stop_words(words):
    parts = []
    for raw in words:
        phrase = str(raw).strip()
        if not phrase:
            continue
        body = r'\s+'.join(re.escape(word) for word in phrase.split())
        parts.append(rf'(?<!\w){body}\w*')
    if not parts:
        return re.compile(r'(?!)', re.IGNORECASE)
    return re.compile('|'.join(parts), re.IGNORECASE)


def stop_word_hits(url, response, pattern):
    if response.status_code != 200:
        return []
    kind = _scan_kind(response.get('Content-Type', ''))
    if not kind:
        return []
    raw = response.content.decode(getattr(response, 'charset', None) or 'utf-8', errors='replace')
    if kind == 'html':
        parser = _VisibleParts()
        parser.feed(raw)
        parser.close()
        chunks = parser.chunks()
    else:
        chunks = [('body', raw)]
    found = []
    seen = set()
    for place, text in chunks:
        compact = re.sub(r'\s+', ' ', text or '').strip()
        if not compact:
            continue
        for match in pattern.finditer(compact):
            word = match.group(0)
            key = (url, place, word.casefold())
            if key in seen:
                continue
            seen.add(key)
            found.append(f'{url} | {place} | {word}')
    return found


def _crawl_urls(client, prefix):
    urls = list(discover_public_paths(client, prefix))
    seen = set(urls)
    for path in spider_extra_paths():
        url = prefix_path(prefix, path)
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


class ExchangeOnlySpiderTests(RealDataTestCase):
    def test_public_pages_hide_stop_words(self):
        _kind, why = classify_eur_usd()
        print(why)
        try:
            from src.core.exchange_stopwords import STOP_WORDS
        except ImportError:
            STOP_WORDS = None
        if STOP_WORDS is None:
            self.fail('src.core.exchange_stopwords відсутній (гілка eo/filter не злита)')
        pattern = compile_stop_words(STOP_WORDS)
        report = []
        violations = []
        env = {'EXCHANGE_ONLY_MODE': '1', 'HIDDEN_PAGE_STATUS': '503'}
        try:
            with patch.dict(os.environ, env):
                cache.clear()
                self.client.raise_request_exception = False
                for code, prefix in language_prefixes():
                    report.append(f'[{code}]')
                    with translation.override(code):
                        urls = _crawl_urls(self.client, prefix)
                        for url in urls:
                            response = self.client.get(url, follow=True)
                            report.append(f'{response.status_code} {url}')
                            if response.status_code in (404, 503):
                                continue
                            violations.extend(stop_word_hits(url, response, pattern))
                    report.append('')
        finally:
            text = '\n'.join(report).rstrip() + '\n'
            SPIDER_URLS_FILE.write_text(text, encoding='utf-8')
            print(text)
        self.assertFalse(
            violations,
            'Стоп-слова у режимі «лише обмін»:\n' + '\n'.join(violations),
        )
