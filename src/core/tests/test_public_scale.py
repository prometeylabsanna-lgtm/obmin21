import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ROOT = Path(settings.BASE_DIR)
_CSS = _ROOT / 'src/core/static/css'
_HAIRLINE = (0.0, 1.0, 2.0)
_NUM_PX = re.compile(r'(?:\d+\.\d+|\d+|\.\d+)px', re.I)
_SCALE_FN = re.compile(r'(?<![\w-])scale\(')
_ZOOM = re.compile(r'(?<![\w-])zoom\b')
_PRELUDE_AT = ('@media', '@supports', '@container')
_MEDIA_PRELUDE = re.compile(r'@(?:media|supports|container)\b[^{]*\{')


def _is_hairline(number):
    return abs(float(number)) in _HAIRLINE


def _skip_comment(css, index):
    end = css.find('*/', index + 2)
    return len(css) if end < 0 else end + 2


def _skip_string(css, index):
    quote = css[index]
    cursor = index + 1
    limit = len(css)
    while cursor < limit:
        if css[cursor] == '\\':
            cursor += 2
            continue
        if css[cursor] == quote:
            return cursor + 1
        cursor += 1
    return limit


def _prelude_name(css, index):
    if css[index] != '@':
        return None
    for name in _PRELUDE_AT:
        if not css.startswith(name, index):
            continue
        nxt = index + len(name)
        if nxt < len(css) and (css[nxt].isalnum() or css[nxt] in '-_'):
            continue
        return name
    return None


def _match_px(css, index):
    sign = ''
    cursor = index
    if css[index] in '+-' and (
        index == 0 or css[index - 1].isspace() or css[index - 1] in ':,{(['
    ):
        if index + 1 < len(css) and (css[index + 1].isdigit() or css[index + 1] == '.'):
            sign = css[index]
            cursor = index + 1
        else:
            return None
    matched = _NUM_PX.match(css, cursor)
    if not matched:
        return None
    number = matched.group(0)[:-2]
    return matched.end(), f'{sign}{number}', number


def _public_css():
    for path in sorted(_CSS.rglob('*.css')):
        if 'admin' in path.parts:
            continue
        yield path


class PublicScaleTests(SimpleTestCase):
    def test_scale_token_and_no_zoom_or_scale_function(self):
        variables = (_CSS / 'variables.css').read_text(encoding='utf-8')
        self.assertIn('--scale: 0.9;', variables)
        self.assertIn('--scale: 1.125;', variables)
        self.assertIn('--header-h: calc(72px * var(--scale));', variables)
        self.assertIn('--border-w: 1px;', variables)
        self.assertIn('env(safe-area-inset-bottom, 0px)', variables)
        self.assertRegex(variables, r'@media \(min-width: 768px\)')
        self.assertNotIn('zoom', variables)

        for path in _public_css():
            text = path.read_text(encoding='utf-8')
            self.assertIsNone(
                _ZOOM.search(text),
                f'{path.name} містить zoom',
            )
            self.assertIsNone(
                _SCALE_FN.search(text),
                f'{path.name} містить scale()',
            )
            for prelude in _MEDIA_PRELUDE.finditer(text):
                chunk = prelude.group(0)
                self.assertNotIn('var(--scale)', chunk, path.name)
                self.assertNotIn('calc(', chunk, path.name)
            self._assert_px_scaled(path.name, text)

        for path in sorted((_CSS / 'admin').glob('*.css')):
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('var(--scale)', text, path.name)
            self.assertNotIn('--scale', text, path.name)

    def _assert_px_scaled(self, name, css):
        index = 0
        limit = len(css)
        while index < limit:
            if css.startswith('/*', index):
                index = _skip_comment(css, index)
                continue
            if css[index] in '"\'':
                index = _skip_string(css, index)
                continue
            prelude = _prelude_name(css, index)
            if prelude:
                index += len(prelude)
                while index < limit and css[index] != '{':
                    if css.startswith('/*', index):
                        index = _skip_comment(css, index)
                        continue
                    if css[index] in '"\'':
                        index = _skip_string(css, index)
                        continue
                    index += 1
                continue
            found = _match_px(css, index)
            if not found:
                index += 1
                continue
            end, token, number = found
            followed = css[end:end + len(' * var(--scale))')]
            wrapped = followed == ' * var(--scale))' and css[index - 5:index] == 'calc('
            if _is_hairline(number):
                self.assertFalse(
                    wrapped,
                    f'{name}: {token} не треба масштабувати',
                )
            else:
                self.assertTrue(
                    wrapped,
                    f'{name}: {token} без var(--scale)',
                )
            index = end
